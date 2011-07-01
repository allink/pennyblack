from django.contrib import admin
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response

from pennyblack.forms import CollectionSelectForm

import exceptions

class NewsletterReceiverMixin(object):
    """
    Mixin for every object that can receive a newsletter
    """    
    def get_email(self):
        if hasattr(self,'email'):
            return self.email
        raise exceptions.NotImplementedError('Need a get_email implementation.')
    
    def on_bounce(self, mail):
        pass
        
class JobUnitMixin(object):
    """
    Mixin for every object which can be target of a Job
    """    
    def create_newsletter(self, form_data=None):
        """
        Creates a newsletter for every NewsletterReceiverMixin
        """
        from pennyblack.models.job import Job
        if form_data==None:
            collection_name = 'Default'
            queryset = self.get_receiver_queryset()
        else:
            collection_name = ', '.join(form_data['collections'])
            queryset = self.get_receiver_filtered_queryset(**form_data)
        job = Job(group_object=self, collection=collection_name)
        job.save()
        job.create_mails(queryset)
        return job
        
    def get_newsletter_receiver_collections(self):
        """
        Returns a dict of valid receiver collections
        has to be overriden in the object to return a tuple of querysets
        return (('all',{}),)
        {} is used to filter the queryset when evaluating the
        get_receiver_filtered_queryset function.
        """
        raise exceptions.NotImplementedError("Override this method in your class!")
    
    def get_receiver_queryset(self):
        raise exceptions.NotImplementedError("Override this method in your class!")
    
    def get_receiver_filtered_queryset(self, **kwargs):
        """
        Takes the second part of the collections 
        """
        queryset = self.get_receiver_queryset()
        return queryset


class JobUnitAdmin(admin.ModelAdmin):
    """
    Admin model for objects wich are capable of sending newsletters to it's
    members.
    """
    change_form_template = "admin/pennyblack/jobunit/change_form.html"
    collection_select_form = CollectionSelectForm
    collection_selection_form_extra_fields = dict()
    
    def create_newsletter(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        if len(obj.get_newsletter_receiver_collections()) == 1 and len(self.collection_selection_form_extra_fields) == 0:
            # there is only one collection and no options to select
            # -> call create_newsletter directly
            job = obj.create_newsletter()
            return HttpResponseRedirect(reverse('admin:pennyblack_job_change', args=(job.id,)))            
        if request.method == 'POST':
            form = self.collection_select_form(data=request.POST,
                group_object=obj,
                extra_fields=self.collection_selection_form_extra_fields)
            if form.is_valid():
                job = obj.create_newsletter(form_data=form.cleaned_data)
                return HttpResponseRedirect(reverse('admin:pennyblack_job_change', args=(job.id,)))
        else:
            form = self.collection_select_form(group_object=obj,
                extra_fields=self.collection_selection_form_extra_fields)
        info = self.model._meta.app_label, self.model._meta.module_name
        context = {
            'opts':self.model._meta,
            'app_label':self.model._meta.app_label,
            'adminform':form,
            'form_url' : reverse('admin:%s_%s_create_newsletter' % info, args=(obj.id,))
        }
        context.update(csrf(request))
        return render_to_response('admin/pennyblack/jobunit/select_receiver_collection.html',context)
            
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(JobUnitAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.module_name
        my_urls = patterns('',
            url(r'^(?P<object_id>\d+)/create_newsletter/$', self.admin_site.admin_view(self.create_newsletter), name='%s_%s_create_newsletter' % info),
        )
        return my_urls + urls
