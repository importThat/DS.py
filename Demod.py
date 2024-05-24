import numpy as np
import Plot
from matplotlib import pyplot as plt
from scipy import signal

"""
Class with demod functions, ideally this is automated but very much still a work in progress

"""

# TODO
#  Refactor so demod and mod are children of a Signal class


class Demod:
    def __init__(self, filename, fs):
        self.samplerate = None
        self.samples = np.array([])
        self.fn = filename

        if fs:
            self.fs = fs
        else:
            self.fs = None

        self.f = None

        self.read_file()

        if self.fs and (len(self.samples) > 0):
            self.dur = len(self.samples) / self.fs
        else:
            self.dur = None

    def read_file(self, folder=""):
        file = folder + self.fn
        self.samples = np.fromfile(file, np.complex64)

    def normalise_pwr(self):
        """
        normalises samples to be between 1 and 0
        """
        max_real = max(abs(self.samples.real))
        max_imag = max(abs(self.samples.imag))

        max_val = max(max_imag, max_real)
        self.samples = (self.samples / max_val)

    def trim_by_power(self, padding=10, std_cut = 8):
        """
        Trims the signal by looking at the power envelope. Adds a slight padding to each end to ensure we're
        not losing data
        """
        # TODO
        #  Currently over trims!
        # Find the power
        power = abs(self.samples)
        # We need to look for the first big spike and the last big spike
        pwr_diff = np.gradient(power)
        # the first big positive spike will be it turning on
        sdev = np.std(pwr_diff)
        av = np.mean(pwr_diff)

        # N stds from mean
        sdevs = (pwr_diff - av) / sdev
        index = np.arange(len(sdevs))[abs(sdevs) > std_cut]

        # first is the turn on (hopefully) last is turn off (hopefully)
        first_ind = index[0] - int(padding)
        if first_ind < 0:
            first_ind = 0

        last_ind = index[-1] + int(padding)

        self.samples = self.samples[first_ind:last_ind]

    def detect_params(self):
        """
        detects the parameters of the sample if it follows the GQRX naming convention
        """
        if "_" in self.fn:
            params = self.fn.split("_")
        else:
            raise ValueError("Capture does not appear to be in gqrx format")

        if params[0] != "gqrx":
            raise ValueError("Capture does not appear to be in gqrx format")

        else:
            try:
                self.fs = int(params[3])
                self.f = int(params[4])
            except:
                raise ValueError("Capture does not appear to be in gqrx format")

    def move_freq(self, freq_offset):
        """
        Move the signal by the freq_offset
        """

        # *** Create new samples ***
        # Time vector
        t = 1/self.fs * np.arange(self.dur*self.fs)

        angle = 2 * np.pi * freq_offset * t
        bb_samples = np.cos(angle) + 1j * np.sin(angle)

        if len(bb_samples) > len(self.samples):
            bb_samples = bb_samples[0:len(self.samples)]

        assert len(bb_samples) == len(self.samples), f"BB samples are of different length!"

        self.samples = self.samples * bb_samples

    def exponentiate(self, order=4):
        """
        Raises a signal to the nth power to find the frequency offset and the likely samples per symbol
        """
        # copy the samples and raise to the order
        samps = self.samples.copy()
        samps = samps**order

        # Take the fft to find the freq and sps spikes
        ffts = np.fft.fftshift(np.abs(np.fft.fft(samps)))
        axis = np.arange(self.fs / -2, self.fs / 2, self.fs / len(self.samples))

        # Get indices of the 1 largest element, which will be the freq spike
        largest_inds = np.argpartition(ffts, -1)[-1:]
        largest_val = axis[largest_inds]

        # The frequency offset
        freq = largest_val / order
        freq = round(freq[0]) # Make an int

        plt.plot(axis, ffts)

        return freq

    def QAM(self, c):
        """
        Converts the samples in memory to the closest symbols found in a given constellation plot and returns the
        output
        """
        symbols = np.arange(len(c.map))
        out = []
        for sample in self.samples:
            index = (np.abs(c.map - sample)).argmin()
            out.append(symbols[index])

        return out

    def phase_offset(self, angle=40):
        """
        Adds a phase offset of x degrees to the signal
        """
        # degrees to radians
        phase_offset = angle*np.pi / 180

        z = 1 * np.cos(phase_offset) + 1j * np.sin(phase_offset)

        self.samples = self.samples * z

    def resample(self, up=16, down=1):
        """
        A simple wrapper for scipy's resample
        """
        self.samples = signal.resample_poly(self.samples, up, down)

    def specgram(self, nfft=1024):
        # Nfft shouldn't be bigger than the samples
        if nfft >= len(self.samples):
            nfft = int(len(self.samples)/4)

        kwargs = {"type": "specgram",
                "nfft": nfft,
                "fs": self.fs,
                "title": f"Specgram at Baseband (NFFT={nfft})"}

        Plot.plot(self.samples, **kwargs)

    def psd(self, nfft=1024):
        kwargs = {"type": "psd",
                  "nfft": nfft,
                  "fs": self.fs,
                  "title": f"PSD at Baseband (NFFT={nfft})"}
        Plot.plot(self.samples, **kwargs)

    def iq(self):
        kwargs = {"type": "iq",
                  "title": "IQ Scatter"}

        Plot.plot(self.samples, **kwargs)

    def fft(self, nfft=1024):
        kwargs = {"type": "fft",
                  "title": "FFT of Signal",
                  "fs": self.fs,
                  "nfft": nfft}
        Plot.plot(self.samples, **kwargs)

    def time(self):
        t = 1 / self.fs * np.arange(self.dur * self.fs)
        t = t[0:len(self.samples)]

        kwargs = {"type": "time",
                  "t": t,
                  "title": "Time Domain"}

        Plot.plot(self.samples, **kwargs)


