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

from rest_framework.response import Response
from django.db import transaction
from django.conf import settings
from storageadmin.models import (SambaShare, Disk, User, SambaCustomConfig)
from storageadmin.serializers import SambaShareSerializer
from storageadmin.util import handle_exception
import rest_framework_custom as rfc
from share_helpers import validate_share
from system.samba import (refresh_smb_config, status, restart_samba)
from fs.btrfs import (mount_share, is_share_mounted)

import logging
logger = logging.getLogger(__name__)

class SambaMixin(object):
    serializer_class = SambaShareSerializer
    DEF_OPTS = {
        'comment': 'samba export',
        'browsable': 'yes',
        'guest_ok': 'no',
        'read_only': 'no',
        'custom_config': None,
    }
    BOOL_OPTS = ('yes', 'no',)

    @staticmethod
    def _restart_samba():
        out = status()
        if (out[2] == 0):
            restart_samba()

    @classmethod
    def _validate_input(cls, request, smbo=None):
        options = {}
        def_opts = cls.DEF_OPTS
        if (smbo is not None):
            def_opts = self.DEF_OPTS.copy()
            def_opts['comment'] = smbo.comment
            def_opts['browsable'] = smbo.browsable
            def_opts['guest_ok'] = smbo.guest_ok
            def_opts['read_only'] = smbo.read_only

        options['comment'] = request.data.get('comment', def_opts['comment'])
        options['browsable'] = request.data.get('browsable',
                                                def_opts['browsable'])

        options['custom_config'] = request.data.get('custom_config', [])
        if (type(options['custom_config']) != list):
            e_msg = ('custom config must be a list of strings')
            handle_exception(Exception(e_msg), request)
        if (options['browsable'] not in cls.BOOL_OPTS):
            e_msg = ('Invalid choice for browsable. Possible '
                     'choices are yes or no.')
            handle_exception(Exception(e_msg), request)
        options['guest_ok'] = request.data.get('guest_ok',
                                               def_opts['guest_ok'])
        if (options['guest_ok'] not in cls.BOOL_OPTS):
            e_msg = ('Invalid choice for guest_ok. Possible '
                     'options are yes or no.')
            handle_exception(Exception(e_msg), request)
        options['read_only'] = request.data.get('read_only',
                                                def_opts['read_only'])
        if (options['read_only'] not in cls.BOOL_OPTS):
            e_msg = ('Invalid choice for read_only. Possible '
                     'options are yes or no.')
            handle_exception(Exception(e_msg), request)
        return options


class SambaListView(SambaMixin, rfc.GenericView):
    def get_queryset(self, *args, **kwargs):
        if ('id' in self.kwargs):
            self.paginate_by = 0
            try:
                return SambaShare.objects.get(id=self.kwargs['id'])
            except:
                return []
        return SambaShare.objects.all()

    @transaction.atomic
    def post(self, request):
        if ('shares' not in request.data):
            e_msg = ('Must provide share names')
            handle_exception(Exception(e_msg), request)
        shares = [validate_share(s, request) for s in request.data['shares']]
        options = self._validate_input(request)
        custom_config = options['custom_config']
        del(options['custom_config'])
        for share in shares:
            if (SambaShare.objects.filter(share=share).exists()):
                e_msg = ('Share(%s) is already exported via Samba' %
                         share.name)
                handle_exception(Exception(e_msg), request)
        with self._handle_exception(request):
            for share in shares:
                mnt_pt = ('%s%s' % (settings.MNT_PT, share.name))
                options['share'] = share
                options['path'] = mnt_pt
                smb_share = SambaShare(**options)
                smb_share.save()
                for cc in custom_config:
                    cco = SambaCustomConfig(smb_share=smb_share,
                                            custom_config=cc)
                    cco.save()
                if (not is_share_mounted(share.name)):
                    pool_device = Disk.objects.filter(pool=share.pool)[0].name
                    mount_share(share, pool_device, mnt_pt)

                admin_users = request.data.get('admin_users', None)
                if (admin_users is None):
                    admin_users = []
                for au in admin_users:
                    auo = User.objects.get(username=au)
                    auo.smb_shares.add(smb_share)
            refresh_smb_config(list(SambaShare.objects.all()))
            self._restart_samba()
            return Response(SambaShareSerializer(smb_share).data)


class SambaDetailView(SambaMixin, rfc.GenericView):
    def get(self, *args, **kwargs):
        try:
            data = SambaShare.objects.get(id=self.kwargs['id'])
            serialized_data = SamabShareSerializer(data)
            return Response(serialized_data.data)
        except:
            return Response()

    @transaction.atomic
    def delete(self, request, smb_id):
        try:
            smbo = SambaShare.objects.get(id=smb_id)
            SambaCustomConfig.objects.filter(smb_share=smbo).delete()
            smbo.delete()
        except:
            e_msg = ('Samba export for the id(%s) does not exist' % smb_id)
            handle_exception(Exception(e_msg), request)

        with self._handle_exception(request):
            refresh_smb_config(list(SambaShare.objects.all()))
            self._restart_samba()
            return Response()

    @transaction.atomic
    def put(self, request, smb_id):
        with self._handle_exception(request):
            try:
                smbo = SambaShare.objects.get(id=smb_id)
            except:
                e_msg = ('Samba export for the id(%s) does not exist' % smb_id)
                handle_exception(Exception(e_msg), request)

            options = self._validate_input(request)
            custom_config = options['custom_config']
            del(options['custom_config'])
            smbo.__dict__.update(**options)
            admin_users = request.data.get('admin_users', None)
            if (admin_users is None):
                admin_users = []
            for uo in User.objects.filter(smb_shares=smbo):
                if (uo.username not in admin_users):
                    uo.smb_shares.remove(smbo)
            for u in admin_users:
                if (not User.objects.filter(username=u,
                                            smb_shares=smbo).exists()):
                    auo = User.objects.get(username=u)
                    auo.smb_shares.add(smbo)
            smbo.save()
            for cco in SambaCustomConfig.objects.filter(smb_share=smbo):
                if (cco.custom_config not in custom_config):
                    cco.delete()
                else:
                    custom_config.remove(cco.custom_config)
            for cc in custom_config:
                cco = SambaCustomConfig(smb_share=smbo, custom_config=cc)
                cco.save()
            for smb_o in SambaShare.objects.all():
                if (not is_share_mounted(smb_o.share.name)):
                    pool_device = Disk.objects.filter(
                        pool=smb_o.share.pool)[0].name
                    mnt_pt = ('%s%s' % (settings.MNT_PT, smb_o.share.name))
                    try:
                        mount_share(smb_o.share, pool_device, mnt_pt)
                    except Exception, e:
                        logger.exception(e)
                        if (smb_o.id == smbo.id):
                            e_msg = ('Failed to mount share(%s) due to a low '
                                     'level error.' % smb_o.share.name)
                            handle_exception(Exception(e_msg), request)

            refresh_smb_config(list(SambaShare.objects.all()))
            self._restart_samba()
            return Response(SambaShareSerializer(smbo).data)
