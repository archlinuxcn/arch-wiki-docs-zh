#!/usr/bin/python3

import datetime
import sys

import ws.ArchWiki.lang as lang
import ws.config
from ws.client import API

import ArchWiki

def print_namespaces(api: API) -> None:
    for id_ in sorted(api.site.namespaces.keys()):
        ns = api.site.namespaces[id_]["*"]
        if ns == "":
            ns = "Main"
        print("  %2d -- %s" % (id_, ns))

if __name__ == "__main__":
    argparser = ws.config.getArgParser(description="Download pages from Arch Wiki and optimize them for offline browsing")
    API.set_argparser(argparser)

    group = argparser.add_argument_group(title="script parameters")
    group.add_argument("--output-directory", type=str, required=True, help="Path where the downloaded pages should be stored.")
    group.add_argument("--force", action="store_true", help="Ignore timestamp, always download the page from the wiki.")
    group.add_argument("--clean", action="store_true", help="Clean the output directory after downloading, useful for removing pages deleted/moved on the wiki. Warning: any unknown files found in the output directory will be deleted!")
    group.add_argument("--safe-filenames", action="store_true", help="Force using ASCII file names instead of the default Unicode.")
    group.add_argument("--variant", type=str, required=True, help="zh variant")

    args = ws.config.parse_args(argparser)

    if args.force:
        epoch = datetime.datetime.now(datetime.UTC)
    else:
        # this should be the date of the latest incompatible change
        epoch = datetime.datetime(2026, 1, 2, 0, 0, 0, tzinfo=datetime.UTC)

    sys.stdout.reconfigure(line_buffering=True)
    api = API.from_argparser(args)
    optimizer = ArchWiki.Optimizer(api, args.output_directory, args.safe_filenames, variant=args.variant)

    downloader = ArchWiki.Downloader(api, args.output_directory, epoch, optimizer=optimizer, variant=args.variant)
    downloader.download_css()
    print_namespaces(api)
    for ns in ["0", "4", "12", "14"]:
        downloader.process_namespace(ns)

    downloader.download_images()

    if args.clean:
        downloader.clean_output_directory()
