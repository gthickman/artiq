#!/usr/bin/env python3
# Yann Sionneau <ys@m-labs.hk>, 2015

import argparse

from artiq.protocols.pc_rpc import simple_server_loop
from artiq.devices.pxi6733.driver import DAQmx, DAQmxSim
from artiq.tools import verbosity_args, init_logger, simple_network_args


def get_argparser():
    parser = argparse.ArgumentParser(description="NI PXI 6733 controller")
    simple_network_args(parser, 3256)
    parser.add_argument("-C", "--channels", default=None,
                        help="List of channels (e.g. Dev1/ao0, Dev1/ao1:3)."
                        " Omit for simulation mode.")
    parser.add_argument("-c", "--clock", default="PFI5",
                        help="Input clock pin name (default: PFI5)")
    verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if args.channels is None:
        daq = DAQmxSim()
    else:
        daq = DAQmx(args.channels,
                    args.clock)

    try:
        simple_server_loop({"pxi6733": daq},
                           args.bind, args.port)
    finally:
        daq.close()

if __name__ == "__main__":
    main()
