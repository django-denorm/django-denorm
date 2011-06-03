# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'DirtyInstance.object_id'
        db.alter_column('denorm_dirtyinstance', 'object_id', self.gf('django.db.models.fields.TextField')(null=True))


    def backwards(self, orm):
        
        # Changing field 'DirtyInstance.object_id'
        db.alter_column('denorm_dirtyinstance', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))


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
            'object_id': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['denorm']
