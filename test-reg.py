t = "及人矢口戈体"

reg = r'[衫韧初级矢口知认人].*[知认人载体]'

import re
print(re.search(reg, t))
print(re.findall(reg, t))


# import torch

# print(torch.cuda.is_available())
