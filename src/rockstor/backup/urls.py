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

from django.conf.urls import patterns, url
from backup.views import (BackupPolicyView, PolicyTrailView, PluginView)

urlpatterns = patterns(
        '',
        url(r'^$', BackupPolicyView.as_view()),
        url(r'^/trail$', PolicyTrailView.as_view()),
        url(r'^/trail/policy/(?P<pid>\d+)$', PolicyTrailView.as_view()),
        url(r'^/trail/(?P<tid>\d+)$', PolicyTrailView.as_view()),
        url(r'^/plugin/(?P<command>start|stop|status)$',
            PluginView.as_view()),
        url(r'/(?P<id>\d+)$', BackupPolicyView.as_view()),
        )

