# Yann Sionneau <ys@m-labs.hk>, 2015

from ctypes import byref, c_ulong
import numpy as np


class DAQmxSim:
    def load_sample_values(self, values):
        pass

    def close(self):
        pass

    def ping(self):
        return True

def string_to_bytes(string, name):
    if isinstance(string, str):
        string = bytes(string, encoding="ascii")
    elif not isinstance(string, bytes):
        raise ValueError("{} must be of either str or bytes type".format(name))
    return string

class DAQmx:
    """NI PXI6733 DAQ interface."""

    def __init__(self, channels, clock):
        """
        :param channels: List of channels as a string or bytes(), following
            the physical channels lists and ranges NI-DAQmx syntax.

            Example: Dev1/ao0, Dev1/ao1:ao3
        :param clock: Clock source terminal as a string or bytes(), following
            NI-DAQmx terminal names syntax.

            Example: PFI5
        """

        import PyDAQmx as daq

        self.channels = string_to_bytes(channels, "channels")
        self.clock = string_to_bytes(clock, "clock")
        self.task = None
        self.daq = daq

    def done_callback_py(self, taskhandle, status, callback_data):
        if taskhandle == self.task:
            self.clear_pending_task()

    def ping(self):
        try:
            data = (c_ulong*1)()
            self.daq.DAQmxGetDevSerialNum(self.device, data)
        except:
            return False
        return True

    def load_sample_values(self, sampling_freq, values):
        """Load sample values into PXI 6733 device.

        This loads sample values into the PXI 6733 device.
        The device will output samples at each clock rising edge.
        The first sample is output at the first clock rising edge.

        When using several channels simultaneously, you must concatenate the
        values for the different channels in the ``values`` array.
        The sample values for the same channel must be grouped together.

        Example:

        >>> values = np.array([ch0_samp0, ch0_samp1, ch1_samp0, ch1_samp1],
                              dtype=float)

        In this example the first two samples will be output via the first
        channel and the two following samples will be output via the second
        channel.

        Any call to this method will cancel any previous task even if it has
        not yet completed.

        :param sampling_freq: The sampling frequency in samples per second.
        :param values: A numpy array of sample values to load in the device.
        """

        self.clear_pending_task()

        t = self.daq.Task()
        t.CreateAOVoltageChan(self.channels, b"",
                              min(values), max(values),
                              self.daq.DAQmx_Val_Volts, None)

        channel_number = self.daq.int32()
        t.GetTaskNumChans(byref(channel_number))
        nb_values = len(values)
        if nb_values % channel_number.value > 0:
            self.daq.DAQmxClearTask(t.taskHandle)
            raise ValueError("The size of the values array must be a multiple "
                             "of the number of channels ({})"
                             .format(channel_number.value))
        samps_per_channel = nb_values // channel_number

        t.CfgSampClkTiming(self.clock, sampling_freq,
                           self.daq.DAQmx_Val_Rising,
                           self.daq.DAQmx_Val_FiniteSamps, samps_per_channel)
        num_samps_written = self.daq.int32()
        values = np.require(values, dtype=float,
                            requirements=["C_CONTIGUOUS", "WRITEABLE"])
        ret = t.WriteAnalogF64(samps_per_channel, False, 0,
                               self.daq.DAQmx_Val_GroupByChannel, values,
                               byref(num_samps_written), None)
        if num_samps_written.value != nb_values:
            raise IOError("Error: only {} sample values were written"
                          .format(num_samps_written.value))
        if ret:
            raise IOError("Error while writing samples to the channel buffer")

        done_cb = self.daq.DAQmxDoneEventCallbackPtr(self.done_callback_py)
        self.task = t.taskHandle
        self.daq.DAQmxRegisterDoneEvent(t.taskHandle, 0, done_cb, None)
        t.StartTask()

    def clear_pending_task(self):
        """Clear any pending task."""

        if self.task is not None:
            self.daq.DAQmxClearTask(self.task)
            self.task = None

    def close(self):
        """Free any allocated resources."""

        self.clear_pending_task()
