# Lint as: python3
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""Example using PyCoral to classify a given image using an Edge TPU.

To run this code, you must attach an Edge TPU attached to the host and
install the Edge TPU runtime (`libedgetpu.so`) and `tflite_runtime`. For
device setup instructions, see coral.ai/docs/setup.

Example usage:
```
bash examples/install_requirements.sh classify_image.py

python3 examples/classify_image.py \
  --model test_data/mobilenet_v2_1.0_224_inat_bird_quant_edgetpu.tflite  \
  --labels test_data/inat_bird_labels.txt \
  --input test_data/parrot.jpg
```
"""

import argparse
import time
import glob
import numpy as np
from PIL import Image
from pycoral.adapters import classify
from pycoral.adapters import common
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter


def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '-m', '--model', required=True, help='File path of .tflite file.')
  parser.add_argument(
      '-i', '--input', required=True, help='File path of folder images to be classified.')
  parser.add_argument(
      '-l', '--labels', required=True, help='File path of labels file.')
  parser.add_argument(
      '-v', '--vector', required=True, help='File path of true vector label file.')
  parser.add_argument(
      '-k', '--top_k', type=int, default=1,
      help='Max number of classification results')
  parser.add_argument(
      '-t', '--threshold', type=float, default=0.0,
      help='Classification score threshold')
  parser.add_argument(
      '-a', '--input_mean', type=float, default=128.0,
      help='Mean value for input normalization')
  parser.add_argument(
      '-s', '--input_std', type=float, default=128.0,
      help='STD value for input normalization')
  args = parser.parse_args()

  labels = read_label_file(args.labels) if args.labels else {}

  interpreter = make_interpreter(*args.model.split('@'))
  interpreter.allocate_tensors()

  # Model must be uint8 quantized
  if common.input_details(interpreter, 'dtype') != np.uint8:
    raise ValueError('Only support uint8 input type.')

size = common.input_size(interpreter)

rute = args.input

image_rute = glob.glob( rute + "/*.jpg")


params = common.input_details(interpreter, 'quantization_parameters')
scale = params['scales']
zero_point = params['zero_points']
mean = args.input_mean
std = args.input_std
print('Parametros de cuantizacion completados')
true_labels = []
for image in image_rute:
    image_c_r = Image.open(image).convert('RGB').resize(size, Image.LANCZOS)
    print('Completado la conversion a RGB y el resize')
  # Image data must go through two transforms before running inference:
  # 1. normalization: f = (input - mean) / std
  # 2. quantization: q = f / scale + zero_point
  # The following code combines the two steps as such:
  # q = (input - mean) / (std * scale) + zero_point
  # However, if std * scale equals 1, and mean - zero_point equals 0, the input
  # does not need any preprocessing (but in practice, even if the results are
  # very close to 1 and 0, it is probably okay to skip preprocessing for better
  # efficiency; we use 1e-5 below instead of absolute zero).
    if abs(scale * std - 1) < 1e-5 and abs(mean - zero_point) < 1e-5:
    # Input data does not require preprocessing.
      common.set_input(interpreter, image)
    else:
    # Input data requires preprocessing
     normalized_input = (np.asarray(image) - mean) / (std * scale) + zero_point
     np.clip(normalized_input, 0, 255, out=normalized_input)
     common.set_input(interpreter, normalized_input.astype(np.uint8))
     print('Terminado el preprocesamiento')
    

  # Run inference
    interpreter.invoke()
    classes = classify.get_classes(interpreter, args.top_k, args.threshold)

    print('Lo que genera la prediccion es esto:')
    print(classes)
  
    for c in classes:
      print('%s: %.5f' % (labels.get(c.id, c.id), c.score))
    
    # Convertir las etiquetas del lote de formato one-hot encoding a enteros
    etiquetas_enteros = np.argmax(classes, axis=1)
    
    # Extender la lista de etiquetas verdaderas con las etiquetas del lote
    true_labels.extend(etiquetas_enteros)

    print("Termine un ciclo en true_labels")

print("Termine todas las imagenes")
print("---------------------------")
print("TRUE_LABELS:")
print(true_labels)



if __name__ == '__main__':
  main()
