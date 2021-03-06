"""
Copyright (c) 2012-2013 RockStor, Inc. <http://rockstor.com>
This file is part of RockStor.

RockStor is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

RockStor is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from multiprocessing import Process
import subprocess


class PoolBalance(Process):

    def __init__(self, mnt_pt, force=True, convert=None):
        self.mnt_pt = mnt_pt
        self.force = force
        self.convert = convert
        super(PoolBalance, self).__init__()

    def run(self):
        cmd = ['btrfs', 'balance', 'start', self.mnt_pt]
        if (self.force):
            cmd.insert(3, '-f')
        if (self.convert is not None):
            cmd.insert(3, '-dconvert=%s' % self.convert)
            cmd.insert(3, '-mconvert=%s' % self.convert)
        self.sp = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
