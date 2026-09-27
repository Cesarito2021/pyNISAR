"""Portable command line; run the same workflow in any Python environment."""
import argparse
import json


def main():
    parser = argparse.ArgumentParser(prog='pynisar')
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect'); inspect.add_argument('source')
    inspect.add_argument('--frequency', choices=['A', 'B'], default='A')
    demo = sub.add_parser('demo'); demo.add_argument('--output', default='outputs')
    demo.add_argument('--mode', choices=['dual', 'quad'], default='dual')
    demo.add_argument('--figures', action='store_true')
    process = sub.add_parser('process'); process.add_argument('source')
    process.add_argument('--output', default='outputs')
    process.add_argument('--frequency', choices=['A', 'B'], default='A')
    process.add_argument('--channels', nargs='+')
    process.add_argument('--window-size', type=int, default=256)
    process.add_argument('--looks', nargs=2, type=int, default=(1, 1))
    location = process.add_mutually_exclusive_group()
    location.add_argument('--center', nargs=2, type=float, metavar=('LON','LAT'))
    location.add_argument('--pixel', nargs=2, type=int, metavar=('ROW','COL'))
    process.add_argument('--reciprocal', action='store_true')
    args = parser.parse_args()
    import pynisar
    if args.command == 'inspect':
        print(json.dumps(pynisar.inspect(args.source, frequency=args.frequency), indent=2))
    elif args.command == 'demo':
        run = pynisar.process_sample(args.output, mode=args.mode)
        if args.figures:
            pynisar.plot(run); pynisar.report(run)
        print(run)
    else:
        options = vars(args).copy()
        options.pop('command')
        print(pynisar.process(**options))


if __name__ == '__main__':
    main()
