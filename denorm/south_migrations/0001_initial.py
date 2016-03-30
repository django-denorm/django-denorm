# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'DirtyInstance'
        db.create_table('denorm_dirtyinstance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('denorm', ['DirtyInstance'])

        # Adding unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.create_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

    def backwards(self, orm):

        # Removing unique constraint on 'DirtyInstance', fields ['object_id', 'content_type']
        db.delete_unique('denorm_dirtyinstance', ['object_id', 'content_type_id'])

        # Deleting model 'DirtyInstance'
        db.delete_table('denorm_dirtyinstance')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'denorm.dirtyinstance': {
            'Meta': {'unique_together': "(('object_id', 'content_type'),)", 'object_name': 'DirtyInstance'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['denorm']
