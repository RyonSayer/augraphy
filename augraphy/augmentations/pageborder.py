import random

import cv2
import numpy as np

from augraphy.augmentations.lib import warp_fold_left_side
from augraphy.augmentations.lib import warp_fold_right_side
from augraphy.base.augmentation import Augmentation


class PageBorder(Augmentation):
    """Add border effect to sides of input image.

    :param side: One of the four sides of page i:e top,right,left,bottom,random.
                By default it is "random"
    :type side: string , optional
    :param width_range: Pair of ints determining the width of the page border effect.
    :type width_range: tuple, optional
    :param pages: An integer determining the number of page shadows in the border.
    :type pages: int , optional
    :param noise_intensity_range: A pair of floats determining the intensity of
                                  noise being applied around the borders.
    :type noise_intensity_range: tuple , optional
    :param curve_frequency: Number of curvy section in the generated shadow lines.
    :type curve_frequency: tuple, optional
    :param curve_height: Height of curvy section in the generated shadow lines.
    :type curve_height: tuple, optional
    :param curve_length_one_side: Length for one side of generated curvy section.
    :type curve_length_one_side: tuple, optional
    :param value: Pair of ints determining intensity of generated shadow lines.
    :type value: tuple, optional
    :param p: The probability this Augmentation will be applied.
    :type p: float, optional
    """

    def __init__(
        self,
        side="random",
        width_range=(30, 60),
        pages=None,
        noise_intensity_range=(0.3, 0.8),
        curve_frequency=(2, 8),
        curve_height=(2, 4),
        curve_length_one_side=(50, 100),
        value=(30, 120),
        p=1,
    ):
        """Constructor method"""
        super().__init__(p=p)
        self.side = side
        self.width_range = width_range
        self.pages = pages
        self.noise_intensity_range = noise_intensity_range
        self.curve_frequency = curve_frequency
        self.curve_height = curve_height
        self.curve_length_one_side = curve_length_one_side
        self.value = value

    def __repr__(self):
        return f"PageBorder(side={self.side}, width_range={self.width_range}, pages={self.pages}, noise_intensity_range={self.noise_intensity_range}, curve_frequency={self.curve_frequency}, curve_height={self.curve_height}, curve_length_one_side={self.curve_length_one_side}, value={self.value}, p={self.p})"

    def add_corner_noise(self, border, intensity=0.2):

        ksize = (5, 5)
        blur = cv2.blur(border, ksize)

        # create edge in horizontal direction
        edge = np.full((blur.shape[0], blur.shape[1]), fill_value=0, dtype="uint8")
        if len(blur.shape) > 2:
            blur = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
        # get dx
        edge[:, 1:] = blur[:, 1:] - blur[:, :-1]
        edge[:, :-1] += blur[:, :-1] - blur[:, 1:]
        # absolute the dx value and binarize it
        edge = abs(edge)
        edge[edge > 0] = 255

        Y, X = edge.shape
        idx_list = np.where(edge == 255)
        for i in range(len(idx_list[0])):
            x = idx_list[0][i]
            y = idx_list[1][i]

            reps = random.randint(1, 3)
            for i in range(reps):
                if intensity > random.random():
                    # add noise to one side of the line
                    spread = random.randint(1, max(1, int(self.width_range[0] / 18)))
                    d = int(random.uniform(1, spread * 2))
                    border[x, min(X - 1, y + d)] = random.randint(self.value[0], self.value[1])
                    # add noise to another side of the line
                    spread = random.randint(1, max(1, int(self.width_range[0] / 18)))
                    d = int(random.uniform(1, spread * 2))
                    border[x, max(0, y - d)] = random.randint(self.value[0], self.value[1])

        return border

    def random_folding(self, image):

        # rotate image due to folding algorithm process image in another direction
        image_rotate = np.rot90(image, 1)

        # get image x and y size
        ysize, xsize = image_rotate.shape[:2]

        # height of curve, min value is 1
        curve_y_shift = random.randint(max(1, self.curve_height[0]), max(1, self.curve_height[1]))

        # length of one side curvy part, min value is 5
        curve_width_one_side = random.randint(
            max(5, self.curve_length_one_side[0]),
            max(5, self.curve_length_one_side[1]),
        )

        # center of curvy part
        curve_x = random.randint(curve_width_one_side + 1, xsize - curve_width_one_side - 1)

        # filler of folding function
        curve_noise = 0

        # warp image to produce curvy effect
        image_curve_left = warp_fold_left_side(
            image_rotate,
            ysize,
            curve_noise,
            curve_x,
            curve_width_one_side,
            curve_y_shift,
        )

        image_curve_right = warp_fold_right_side(
            image_curve_left,
            ysize,
            curve_noise,
            curve_x,
            curve_width_one_side,
            curve_y_shift,
        )

        # rotate back the image
        image_curve = np.rot90(image_curve_right, 3)

        return image_curve

    def create_border(
        self,
        channel,
        border_width,
        border_height,
        num_pages=None,
        noise_intensity=0.2,
    ):

        pad = 0
        if channel > 2:
            border = np.ones((border_height, border_width + pad, channel))
            random_color = random.randint(self.value[0], self.value[1])
            color = (random_color, random_color, random_color)
        else:
            border = np.ones((border_height, border_width + pad))
            color = random.randint(self.value[0], self.value[1])

        if num_pages is None:
            num_pages = random.randint(3, 6)

        # initialize border image
        border_merged = np.full_like(border, fill_value=255).astype("uint8")
        for x in np.linspace(border_width, 0, num_pages):

            # create a copy of image
            border_single = border.copy() * 255

            # get start and end x
            x = int(x)
            e = (
                border_width
                if x == border_width
                else np.random.randint(
                    int(border_width - (border_width / 2)),
                    border_width,
                )
            )
            start_point = (x, 0)
            end_point = (e, border_height)

            # generate radom thickness and draw line
            thickness = np.random.choice([2, 3, 4])
            border_single = cv2.line(border_single, start_point, end_point, color, thickness)

            # apply random folding
            if x != border_width and border_height > (self.curve_length_one_side[1] * 2) + 2:
                for _ in range(random.randint(self.curve_frequency[0], self.curve_frequency[1])):
                    border_single = self.random_folding(border_single)

            # add noise to single page border
            border_single = self.add_corner_noise(np.uint8(border_single), noise_intensity)

            # merge borders
            border_merged = np.minimum(border_merged, border_single)

        # blur the final merged image
        border_merged = cv2.blur(border_merged, (3, 3))

        return border_merged

    def __call__(self, image, layer=None, force=False):
        if force or self.should_run():
            image = image.copy()

            noise_intensity = random.uniform(
                self.noise_intensity_range[0],
                self.noise_intensity_range[1],
            )
            border_width = random.randint(self.width_range[0], self.width_range[1])

            height, width = image.shape[:2]
            if len(image.shape) > 2:
                channel = image.shape[2]
            else:
                channel = 1

            if self.side == "random":
                side = random.choice(["left", "right", "top", "bottom"])
            else:
                side = self.side

            if side == "top" or side == "bottom":
                height = width

            border = self.create_border(
                channel,
                border_width,
                height,
                self.pages,
                noise_intensity,
            )

            if side == "left":
                image = np.hstack((border, image))
            elif side == "right":
                image = np.hstack((image, np.fliplr(border)))
            elif side == "top":
                image = np.vstack((cv2.rotate(border, cv2.ROTATE_90_CLOCKWISE), image))
            elif side == "bottom":
                image = np.vstack(
                    (image, (cv2.rotate(border, cv2.ROTATE_90_COUNTERCLOCKWISE))),
                )
            return image
