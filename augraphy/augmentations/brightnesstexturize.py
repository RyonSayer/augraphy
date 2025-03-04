import random

import cv2
import numpy as np

from augraphy.base.augmentation import Augmentation


class BrightnessTexturize(Augmentation):
    """Creates a random noise in the brightness channel to emulate paper
    textures.

    :param range: Pair of floats determining the range from which to sample values
           for the brightness matrix. Suggested value = <1.
    :type range: tuple, optional
    :param deviation: Additional variation for the uniform sample.
    :type deviation: float, optional
    :param p: The probability that this Augmentation will be applied.
    :type p: float, optional
    """

    def __init__(self, range=(0.9, 0.99), deviation=0.03, p=1):
        """Constructor method"""
        super().__init__(p=p)
        self.low = range[0]
        self.high = range[1]
        self.deviation = deviation
        self.range = range

    # Constructs a string representation of this Augmentation.
    def __repr__(self):
        return f"BrightnessTexturize(range={self.range}, deviation={self.deviation}, p={self.p})"

    # Applies the Augmentation to input data.
    def __call__(self, image, layer=None, force=False):
        if force or self.should_run():
            image_output = image.copy()

            # for colour image
            if len(image.shape) > 2:
                hsv = cv2.cvtColor(image_output.astype("uint8"), cv2.COLOR_BGR2HSV)
            # for gray image
            else:
                bgr = hsv = cv2.cvtColor(image_output.astype("uint8"), cv2.COLOR_GRAY2BGR)
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            # compute random value
            value = random.uniform(self.low, self.high)
            # convert to float (range 0-1)
            hsv = np.array(hsv, dtype=np.float64)

            # add noise using deviation
            low_value = value - (value * self.deviation)  # *random.uniform(0, deviation)
            max_value = value + (value * self.deviation)

            # apply noise
            makerand = np.vectorize(lambda x: random.uniform(low_value, max_value))
            brightness_matrix = makerand(np.zeros((hsv.shape[0], hsv.shape[1])))
            hsv[:, :, 1] *= brightness_matrix
            hsv[:, :, 2] *= brightness_matrix
            hsv[:, :, 1][hsv[:, :, 1] > 255] = 255
            hsv[:, :, 2][hsv[:, :, 2] > 255] = 255

            # convert back to uint8, apply bitwise not and convert to hsv again
            hsv = np.array(hsv, dtype=np.uint8)
            hsv = cv2.bitwise_not(hsv)
            hsv = np.array(hsv, dtype=np.float64)

            # add noise using deviation again
            low_value = value - (value * self.deviation)
            max_value = value + (value * self.deviation)

            # apply noise again
            makerand = np.vectorize(lambda x: random.uniform(low_value, max_value))
            brightness_matrix = makerand(np.zeros((hsv.shape[0], hsv.shape[1])))
            hsv[:, :, 1] *= brightness_matrix
            hsv[:, :, 2] *= brightness_matrix
            hsv[:, :, 1][hsv[:, :, 1] > 255] = 255
            hsv[:, :, 2][hsv[:, :, 2] > 255] = 255

            # convert back to uint8, apply bitwise not
            hsv = np.array(hsv, dtype=np.uint8)
            hsv = cv2.bitwise_not(hsv)

            image_output = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # convert back to gray
            if len(image.shape) < 3:
                image_output = cv2.cvtColor(hsv, cv2.COLOR_BGR2GRAY)

            return image_output
