"""Run from an installed checkout: python examples/process_nisar.py scene.h5."""
import argparse
import pynisar

parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('--output', default='outputs')
args = parser.parse_args()
print(pynisar.inspect(args.source))
run = pynisar.process(args.source, args.output, channels=['HH','HV'], window_size=256, looks=(4,2))
pynisar.plot(run)
pynisar.report(run)
print(run)
