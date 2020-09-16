# Python
import logging
from time import sleep, time

# pyAts
from pyats.async_ import pcall
from pyats.easypy.plugins.bases import BasePlugin

# Logger
log = logging.getLogger('ats.easypy.%s' % __name__)


class TopologyUpPlugin(BasePlugin):
    '''
    Runs before job starts, to verify virtual topology is up and running
    before executing the test script.
    '''

    @classmethod
    def configure_parser(cls, parser, legacy_cli = True):
        grp = parser.add_argument_group('TopologyUpPlugin')

        if legacy_cli:
            all_devices_up = ['-ignore-all-devices-up']
            connection_check_timeout = ['-connection-check-timeout']
            connection_check_interval = ['-connection-check-interval']
        else:
            all_devices_up = ['--ignore-all-devices-up']
            connection_check_timeout = ['--connection-check-timeout']
            connection_check_interval = ['--connection-check-interval']

        # -ignore-all-devices-up
        # --ignore-all-devices-up
        grp.add_argument(*all_devices_up,
                         dest='all_devices_up',
                         action="store",
                         default = None,
                         help='Enable/Disable checking for topology up pre job execution')

        # -connection-check-timeout
        # --connection-check-timeout
        grp.add_argument(*connection_check_timeout,
                         dest='connection_check_timeout',
                         action='store',
                         default=120,
                         help='Total time allowed for checking devices connectivity')

        # -connection-check-interval
        # --connection-check-interval
        grp.add_argument(*connection_check_interval,
                         dest='connection_check_interval',
                         action='store',
                         default=10,
                         help='Time to sleep between device connectivity checks')

        return grp


    def pre_job(self, task):
        '''Try to connect to all the topology devices in parallel and make sure they
           are up and running before executing the test script.
        '''

        # Check for the argument controlling the plugin run
        ignore_devices_up = self.runtime.args.all_devices_up

        if ignore_devices_up:
            log.info("TopologyUp Plugin is disabled, '--ignore-all-devices-up' must be set to True"
                     "in case of pyats runs or '-ignore-all-devices-up' set to True in case of legacy"
                     "easypy runs")
            return

        # Set the timers
        start_time = time()
        timeout = self.runtime.args.connection_check_timeout
        interval = self.runtime.args.connection_check_interval

        log.info("Connectivity check timeout is '{timeout}' and "
            "connectivity check interval is '{interval}'".format(timeout=timeout, interval=interval))

        # Trying to connect to all devices in parallel
        pcall_output = pcall(device_connect,
            ckwargs = {'start_time': start_time, 'timeout': timeout, 'interval': interval},
            ikwargs = [{'device':self.runtime.testbed.devices[dev]} for dev in self.runtime.testbed.devices])

        if not (pcall_output[0] and pcall_output[1]):
            # Terminate testscript
            raise Exception ("Not all the testbed devices are up and ready")

        return


def device_connect(device, start_time, timeout, interval):
    '''Try to connect to the device and if fails, sleep for interval seconds and retry
       till the timeout is reached

        Args:
            device ('obj'): device to use
            start_time ('int'): Current time to calculate the timeout, seconds
            timeout ('int'): Timeout value when reached exit even if failed, seconds
            interval ('int'): Sleep time between retries, seconds

        Returns:
            result(`bool`): Device is successfully connected

        Raises:
            None

    '''

    time_difference = time() - start_time

    while (time() - start_time) < float(timeout):

        try:
            # Connect to the device
            device.connect()

        except:
            # Not ready sleep and retry
            log.info("Connecting to device '{device}' failed. Sleeping for '{interval}' seconds "
                "and retry, remaining time {remaining_time}".format(
                device=device, interval=interval, remaining_time=timeout-time_difference))

            # Sleep for `interval` seconds
            sleep(interval)

            continue

        else:
            log.info("Successfully connected to '{device}'".format(device=device))

            # Return the pcall call with True
            return True

    return False


# entrypoint
topology_up_plugin = {
    'plugins': {
        'TopologyUpPlugin': {
            'class': TopologyUpPlugin,
            'enabled': True,
            'kwargs': {},
            'module': 'pyats.contrib.plugins.topoup_plugin.topoup',
            'name': 'TopologyUpPlugin'
        }
    }
}
