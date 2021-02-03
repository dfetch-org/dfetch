import os

import spdx_lookup as lookup

def print_match(match, path):
    print(
        f'{path:60s}: {match.license} (confidence: {match.confidence:.1f}%)'
    )


def look_for_licenses(dir):
    for root, dirs, files in os.walk(dir, topdown=False):

        for file in files:

            if file.lower() in ['license', 'copying', 'readme']:
                path = "/".join([root, file])

                with open(path) as f:
                    match = lookup.match(f.read(), threshold=30)

                if match:
                    print_match(match, path)

        for name in dirs:

            path = "/".join([root, name])
            match = lookup.match_path(path, threshold=94)

            if match:
                print_match(match, "/".join([path, match.filename]))


look_for_licenses("Core/Modules")