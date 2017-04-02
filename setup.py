# License for the Dodixie project, originally found here:
# https://github.com/parkerhoyes/dodixie
#
# Copyright (C) 2017 Parker Hoyes <contact@parkerhoyes.com>
#
# This software is provided "as-is", without any express or implied warranty. In
# no event will the authors be held liable for any damages arising from the use of
# this software.
#
# Permission is granted to anyone to use this software for any purpose, including
# commercial applications, and to alter it and redistribute it freely, subject to
# the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not claim
#    that you wrote the original software. If you use this software in a product,
#    an acknowledgment in the product documentation would be appreciated but is
#    not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

# Check Python version
import sys
if sys.version_info.major != 3:
    raise RuntimeError("Python 3 is required")

from distutils.core import setup

setup(name='Dodixie',
      version="0.0.0",
      author="Parker Hoyes",
      author_email="contact@parkerhoyes.com",
      url="https://github.com/parkerhoyes/dodixie",
      packages=['dodixie'])
