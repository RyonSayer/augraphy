import os
import random
from glob import glob

import cv2
import numpy as np

from augraphy.augmentations.lib import sobel
from augraphy.base.augmentation import Augmentation
from augraphy.utilities import *


class BleedThrough(Augmentation):
    """Emulates bleed through effect from the combination of ink bleed and
    gaussian blur operations.

    :param intensity_range: Pair of floats determining the range from which
           noise intensity is sampled.
    :type intensity: tuple, optional
    :param color_range: Pair of ints determining the range from which color
           noise is sampled.
    :type color_range: tuple, optional
    :param ksize: Tuple of height/width pairs from which to sample the kernel
           size. Higher value increases the spreadness of bleeding effect.
    :type ksizes: tuple, optional
    :param sigmaX: Standard deviation of the kernel along the x-axis.
    :type sigmaX: float, optional
    :param alpha: Intensity of bleeding effect, recommended value range from
            0.1 to 0.5.
    :type alpha: float, optional
    :param offsets: Tuple of x and y offset pair to shift the bleed through
            effect from original input.
    :type offsets: tuple, optional
    :param dpi: DPI of foreground image for bleedthrough effect.
            Select either 100, 200 or 300.
    :type dpi: int, optional
    :param p: The probability this Augmentation will be applied.
    :type p: float, optional
    """

    def __init__(
        self,
        intensity_range=(0.1, 0.2),
        color_range=(0, 224),
        ksize=(17, 17),
        sigmaX=0,
        alpha=0.3,
        offsets=(10, 20),
        dpi=100,
        p=1,
    ):
        super().__init__(p=p)
        self.intensity_range = intensity_range
        self.color_range = color_range
        self.ksize = ksize
        self.sigmaX = sigmaX
        self.alpha = alpha
        self.offsets = offsets
        self.dpi = dpi

    # Constructs a string representation of this Augmentation.
    def __repr__(self):
        return f"BleedThrough(intensity_range={self.intensity_range}, color_range={self.color_range}, ksize={self.ksize}, sigmaX={self.sigmaX},alpha={self.alpha},offsets={self.offsets},dpi={self.dpi},p={self.p})"

    # Blend images to produce bleedthrough effect
    def blend(self, img, img_bleed, alpha):

        # convert to single channel to avoud unnecessary noise in colour image
        if len(img_bleed.shape) > 2:
            img_bleed_input = cv2.cvtColor(img_bleed.astype("uint8"), cv2.COLOR_BGR2GRAY)
        else:
            img_bleed_input = img_bleed.astype("uint8")

        ob = OverlayBuilder("normal", img_bleed_input, img, 1, (1, 1), "center", 0, self.alpha)
        return ob.build_overlay()

    # Offset image so that bleedthrough effect is visible and not stacked with input image
    def generate_offset(self, img_bleed, offsets):
        x_offset = offsets[0]
        y_offset = offsets[1]
        if (x_offset == 0) and (y_offset == 0):
            return img_bleed
        elif x_offset == 0:
            img_bleed[y_offset:, :] = img_bleed[:-y_offset, :]
        elif y_offset == 0:
            img_bleed[:, x_offset:] = img_bleed[:, :-x_offset]
        else:
            img_bleed[y_offset:, x_offset:] = img_bleed[:-y_offset, :-x_offset]
        return img_bleed

    # Preprocess and create bleeding ink effect
    def generate_bleeding_ink(self, img, intensity_range, color_range, ksize, sigmaX):
        intensity = random.uniform(intensity_range[0], intensity_range[1])
        add_noise_fn = (
            lambda x, y: random.randint(color_range[0], color_range[1])
            if (y == 255 and random.random() < intensity)
            else x
        )
        add_noise = np.vectorize(add_noise_fn)
        sobelized = sobel(img)
        img_noise = np.double(add_noise(img, sobelized))
        img_bleed = cv2.GaussianBlur(img_noise, ksize=ksize, sigmaX=sigmaX)
        return img_bleed

    # create foreground image for bleedthrough effect
    def create_bleedthrough_foreground(self, image):

        try:
            # Id for figshare published grayscale image
            if self.dpi == 300:
                article_ID = "19227981"
            elif self.dpi == 200:
                article_ID = "19227879"
            else:
                article_ID = "19210698"

            # path to foreground folder
            foreground_folder = os.path.join(os.getcwd() + "/figshare_bleedthrough/")

            # create figshare downloader
            fsdl = FigshareDownloader(directory="figshare_BleedThrough/")

            # download files
            fsdl.download_random_file_from_article(article_ID)

            # file path list
            foreground_images_path = glob(foreground_folder + "*.png", recursive=True)

            # get random image path
            random_path = foreground_images_path[random.randint(0, len(foreground_images_path) - 1)]

            # get random image
            image_bleedthrough_foreground = cv2.imread(random_path)

            # resize foreground
            image_bleedthrough_foreground = cv2.resize(
                image_bleedthrough_foreground,
                (image.shape[1], image.shape[0]),
                interpolation=cv2.INTER_AREA,
            )

        # failed to download, flip and mirror image to get bleedthrough foreground
        except Exception:

            image_flip = cv2.flip(image, 0)
            image_bleedthrough_foreground = cv2.flip(image_flip, 1)

        return image_bleedthrough_foreground

    # Applies the Augmentation to input data.
    def __call__(self, image, layer=None, force=False):
        if force or self.should_run():
            image = image.copy()

            image_bleedthrough_foreground = self.create_bleedthrough_foreground(image)

            image_bleed = self.generate_bleeding_ink(
                image_bleedthrough_foreground,
                self.intensity_range,
                self.color_range,
                self.ksize,
                self.sigmaX,
            )
            image_bleed_offset = self.generate_offset(image_bleed, self.offsets)
            image_bleedthrough = self.blend(image, image_bleed_offset, self.alpha)

            return image_bleedthrough
