import argparse

from simtk.openmm.app import *
from simtk.openmm import *
import simtk.unit as u
from sys import stdout, exit
import os
import socket
import numpy as np


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run an MD simulation using OpenMM')

    parser.add_argument(
        'file',
        metavar='outout.dcd',
        help='the output .dcd file',
        type=str)

    parser.add_argument(
        '-l', '--length', dest='length',
        type=int, default=100, nargs='?',
        help='the number of frames to be simulated')

    parser.add_argument(
        '--store-interval', dest='interval_store',
        type=int, default=100, nargs='?',
        help='store every nth interval')

    parser.add_argument(
        '--report-interval', dest='interval_report',
        type=int, default=100, nargs='?',
        help='report every nth interval')

    parser.add_argument(
        '-s', '--system', dest='system_xml',
        type=str, default='system.xml', nargs='?',
        help='the path to the system.xml file')

    parser.add_argument(
        '--restart', dest='restart',
        type=str, default='', nargs='?',
        help='the path to the restart file. If given the coordinates in the topology file '
             'will be ignored.')

    parser.add_argument(
        '-i', '--integrator', dest='integrator_xml',
        type=str, default='integrator.xml', nargs='?',
        help='the path to the integrator.xml file')

    parser.add_argument(
        '-t', '--topology', dest='topology_pdb',
        type=str, default='topology.pdb', nargs='?',
        help='the path to the topology.pdb file')

    parser.add_argument(
        '-v', '--verbose',
        dest='verbose', action='store_true',
        default=False,
        help='if set then text output is send to the ' +
             'console.')

    # add further auto options here
    platform_properties = {
        'CUDA': ['CUDA_DEVICE_INDEX', 'CUDA_PRECISION']
    }

    for p in platform_properties:
        for v in platform_properties[p]:
            parser.add_argument(
                '--' + v.lower().replace('_', '-'),
                dest=v.lower(), type=str,
                default="",
                help='If not set the environment variable %s will be used instead.' % v)

    parser.add_argument(
        '-r', '--report',
        dest='report', action='store_true',
        default=False,
        help='if set then a report is send to STDOUT')

    parser.add_argument(
        '-p', '--platform', dest='platform',
        type=str, default='fastest', nargs='?',
        help='the platform to be used')

    parser.add_argument(
        '--temperature',
        type=int, default=300,
        help='temperature if not given in integrator xml')

    args = parser.parse_args()

    properties = None

    if args.platform in platform_properties:
        properties = {}
        vars = platform_properties[args.platform]
        for v in vars:
            value = os.environ.get(v, None)
            if hasattr(args, v.lower()):
                value = getattr(args, v.lower())

            if value:
                properties[
                    ''.join([x[0] + x[1:].lower() for x in v.split('_')])
                ] = value

    if args.platform == 'fastest':
        platform = None
    else:
        platform = Platform.getPlatformByName(args.platform)

    pdb = PDBFile(args.topology_pdb)

    with open(args.system_xml) as f:
        system_xml = f.read()
        system = XmlSerializer.deserialize(system_xml)

    with open(args.integrator_xml) as f:
        integrator_xml = f.read()
        integrator = XmlSerializer.deserialize(integrator_xml)

    try:
        simulation = Simulation(
            pdb.topology,
            system,
            integrator,
            platform,
            properties
        )
    except Exception:
        print('EXCEPTION', (socket.gethostname()))
        raise

    print('# platforms available')
    for no_platform in range(Platform.getNumPlatforms()):
        # noinspection PyCallByClass,PyTypeChecker
        print('(%d) %s' % (no_platform, Platform.getPlatform(no_platform).getName()))

    print('# platform used:', simulation.context.getPlatform().getName())

    print(os.environ)

    print(Platform.getPluginLoadFailures())
    print(Platform.getDefaultPluginsDirectory())

    try:
        temperature = integrator.getTemperature()
    except AttributeError:
        assert args.temperature > 0
        temperature = args.temperature * u.kelvin

    print('# temperature:', temperature)

    if args.restart:
        os.link(args.restart, 'input.restart.npz')
        arr = np.load('input.restart.npz')
        simulation.context.setPositions(arr['positions'] * u.nanometers)
        simulation.context.setVelocities(arr['velocities'] * u.nanometers/u.picosecond)
        simulation.context.setPeriodicBoxVectors(*arr['box_vectors'] * u.nanometers)
    else:
        simulation.context.setPositions(pdb.positions)
        pbv = pdb.getTopology().getPeriodicBoxVectors()
        simulation.context.setPeriodicBoxVectors(*pbv)
        # set velocities to temperature in integrator
        simulation.context.setVelocitiesToTemperature(temperature)

    simulation.reporters.append(DCDReporter(args.file, args.interval_store))

    if args.report:
        simulation.reporters.append(
            StateDataReporter(
                stdout,
                args.interval_report,
                step=True,
                potentialEnergy=True,
                temperature=True))

    restart_file_name = args.file + '.restart'

    simulation.step(args.length * args.interval_store)

    state = simulation.context.getState(getPositions=True, getVelocities=True)
    pbv = state.getPeriodicBoxVectors(asNumpy=True)
    vel = state.getVelocities(asNumpy=True)
    pos = state.getPositions(asNumpy=True)

    # dirty hack, but numpy cannot save without an additional extension
    np.savez('output.restart.npz', positions=pos, box_vectors=pbv, velocities=vel, index=args.length)
    os.rename('output.restart.npz', restart_file_name)

    print('Written to file', args.file)
    print('Written to file', restart_file_name)

    exit(0)