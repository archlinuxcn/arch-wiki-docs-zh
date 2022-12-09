#! /usr/bin/env python3

""" Module extending generic MediaWiki interface with stuff specific to ArchWiki
    and some convenient generic methods.
"""

import os.path
import re

from simplemediawiki import MediaWiki

__all__ = ["ArchWiki"]

url = "https://wiki.archlinuxcn.org/wzh/api.php"

class ArchWiki(MediaWiki):

    def __init__(self, **kwargs):
        """ Parameters:
            + all keyword arguments of simplemediawiki.MediaWiki
        """
        super().__init__(url, **kwargs)

        self._namespaces = None
        self._redirects = None

    def query_continue(self, query):
        """ Generator for MediaWiki's query-continue feature.
            ref: https://www.mediawiki.org/wiki/API:Query#Continuing_queries
        """
        last_continue = {"continue": ""}

        while True:
            # clone the original params to clean up old continue params
            query_copy = query.copy()
            # and update with the last continue -- it may involve multiple params,
            # hence the clean up with params.copy()
            query_copy.update(last_continue)
            # call the API and handle the result
            result = self.call(query_copy)
            if "error" in result:
                raise Exception(result["error"])
            if "warnings" in result:
                print(result["warnings"])
            if "query" in result:
                yield result["query"]
            if "continue" not in result:
                break
            last_continue = result["continue"]

    def namespaces(self):
        """ Force the Main namespace to have name instead of empty string.
        """
        if self._namespaces is None:
            self._namespaces = super().namespaces()
            self._namespaces[0] = "Main"
        return self._namespaces

    def print_namespaces(self):
        nsmap = self.namespaces()
        print("Available namespaces:")
        for ns in sorted(nsmap.keys()):
            print("  %2d -- %s" % (ns, nsmap[ns]))

    def detect_namespace(self, title, safe=True):
        """ Detect namespace of a given title.
        """
        pure_title = title
        detected_namespace = self.namespaces()[0]
        match = re.match("^((.+):)?(.+)$", title)
        ns = match.group(2)
        if ns:
            ns = ns.replace("_", " ")
            if ns in self.namespaces().values():
                detected_namespace = ns
                pure_title = match.group(3)
        return pure_title, detected_namespace

    def get_local_filename(self, title, basepath):
        """ Return file name where the given page should be stored, relative to 'basepath'.
        """

        title, namespace = self.detect_namespace(title)

        # be safe and use '_' instead of ' ' in filenames (MediaWiki style)
        title = title.replace(" ", "_")
        namespace = namespace.replace(" ", "_")

        # select pattern per namespace
        if namespace == "Main":
            pattern = "{base}/{langsubtag}/{title}.{ext}"
        elif namespace in ["Talk", "ArchWiki", "ArchWiki_talk", "Template", "Template_talk", "Help", "Help_talk", "Category", "Category_talk"]:
            pattern = "{base}/{langsubtag}/{namespace}:{title}.{ext}"
        elif namespace == "File":
            pattern = "{base}/{namespace}:{title}"
        else:
            pattern = "{base}/{namespace}:{title}.{ext}"

        path = pattern.format(
            base=basepath,
            langsubtag='zh-hans',
            namespace=namespace,
            title=title,
            ext="html"
        )
        return os.path.normpath(path)

    def _fetch_redirects(self):
        """ Fetch dictionary of redirect pages and their targets
        """
        query_allredirects = {
            "action": "query",
            "generator": "allpages",
            "gaplimit": "max",
            "gapfilterredir": "nonredirects",
            "prop": "redirects",
            "rdprop": "title|fragment",
            "rdlimit": "max",
        }
        namespaces = ["0", "4", "12", "14"]

        self._redirects = {}

        for ns in namespaces:
            query_allredirects["gapnamespace"] = ns

            for pages_snippet in self.query_continue(query_allredirects):
                pages_snippet = sorted(pages_snippet["pages"].values(), key=lambda d: d["title"])
                for page in pages_snippet:
                    # construct the mapping, the query result is somewhat reversed...
                    target_title = page["title"]
                    for redirect in page.get("redirects", []):
                        source_title = redirect["title"]
                        target_fragment = redirect.get("fragment")
                        if target_fragment:
                            self._redirects[source_title] = "{}#{}".format(target_title, target_fragment)
                        else:
                            self._redirects[source_title] = target_title

    def redirects(self):
        if self._redirects is None:
            self._fetch_redirects()
        return self._redirects

    def resolve_redirect(self, title):
        """ Returns redirect target title, or given title if it is not redirect.
            The returned title will always contain spaces instead of underscores.
        """
        # the given title must match the format of titles used in self._redirects
        title = title.replace("_", " ")

        return self.redirects().get(title, title)
