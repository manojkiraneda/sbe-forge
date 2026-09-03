#!/usr/bin/env python3
"""Capture Clang's LLVM/Machine IR pass dumps and render HTML diffs."""

import argparse
from pathlib import Path
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--raw-output', required=True)
    parser.add_argument('compiler_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.compiler_args[:1] == ['--']:
        args.compiler_args = args.compiler_args[1:]
    return args


def main() -> int:
    args = parse_args()
    raw_output = Path(args.raw_output)
    command = [
        args.compiler,
        *args.compiler_args,
        '-mllvm', '-print-after-all',
        '-c', args.source,
        '-o', '/dev/null',
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    raw_output.write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        sys.stderr.write(result.stderr)
        return result.returncode

    formatter = Path(__file__).with_name('format_llvm_debug_html.py')
    return subprocess.run([sys.executable, str(formatter), str(raw_output)]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
