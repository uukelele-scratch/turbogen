from PIL import Image
from io import BytesIO


def _rgb_to_number(rgb):
	r, g, b = rgb
	return r * 256**2 + g * 256 + b

def convert_img(img, size):
	img_d = Image.open(BytesIO(img))
	resized_img = img_d.resize((size, size))
	return convert_frame(resized_img, size)

def convert_frame(img,size):
	image_data = []
	for y in range(size):
		row = []
		for x in range(size):
			rgb = img.getpixel((x, y))[:3]
			row.append(_rgb_to_number(rgb))
		image_data.append(row)
	return image_data
