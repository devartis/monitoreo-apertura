# coding=utf-8

from __future__ import unicode_literals

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.conf.urls import url
from django.utils.html import format_html
from django.core.urlresolvers import reverse

from ordered_model.admin import OrderedModelAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from django_datajsonar.admin import AbstractTaskAdmin

from .models import IndicadorRed, Indicador, IndicatorType, TableColumn, HarvestingNode,\
    FederationTask, IndicatorsGenerationTask, ReportGenerationTask
from .tasks import federate_catalogs, federation_run
from .indicators_tasks import generate_indicators
from .report_tasks import send_reports


def switch(field, boolean):
    return lambda _, __, queryset: queryset.update(**{field: boolean})


class TableColumnAdmin(OrderedModelAdmin):
    list_display = ('full_name', 'move_up_down_links')


class IndicatorResource(resources.ModelResource):

    class Meta:
        model = Indicador
        fields = export_order = (
            'fecha',
            'jurisdiccion_nombre',
            'indicador_tipo__nombre',
            'indicador_valor'
        )


class IndicatorAdmin(ImportExportModelAdmin):
    list_filter = ('jurisdiccion_id',)

    resource_class = IndicatorResource


class IndicadorRedResource(resources.ModelResource):
    class Meta:
        model = IndicadorRed
        fields = export_order = (
            'fecha',
            'indicador_tipo__nombre',
            'indicador_valor'
        )


class IndicatorRedAdmin(ImportExportModelAdmin):
    resource_class = IndicadorRedResource


class IndicatorTypeAdmin(OrderedModelAdmin):
    list_display = ('nombre', 'order', 'resumen', 'mostrar', 'move_up_down_links', 'position_actions')
    list_filter = ('resumen', 'mostrar')
    actions = ('queryset_to_top', 'queryset_to_bottom', 'summarize', 'desummarize', 'show', 'hide')

    def get_urls(self):
        urls = super(IndicatorTypeAdmin, self).get_urls()
        extra_urls = [url(r'^(?P<model_id>.+)/(?P<direction>top|bottom)/$', self.order_move, name='order_move'), ]
        return extra_urls + urls

    def position_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Tope</a>&nbsp;'
            '<a class="button" href="{}">Fondo</a>',
            reverse('admin:order_move', args=[obj.pk, 'top']),
            reverse('admin:order_move', args=[obj.pk, 'bottom']),
        )
    position_actions.short_description = 'Posicionamientos'
    position_actions.allow_tags = True

    def order_move(self, request, model_id, direction):
        indicator_type = IndicatorType.objects.get(pk=model_id)
        if direction == 'top':
            indicator_type.top()
        elif direction == 'bottom':
            indicator_type.bottom()
        indicator_type.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    summarize = switch('resumen', True)
    summarize.short_description = 'Agregar al resumen'

    desummarize = switch('resumen', False)
    desummarize.short_description = 'Quitar del resumen'

    show = switch('mostrar', True)
    show.short_description = 'Agregar al reporte'

    hide = switch('mostrar', False)
    hide.short_description = 'Quitar del reporte'


class HarvestingNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'enabled')
    actions = ('federate', 'enable', 'disable')

    enable = switch('enabled', True)
    enable.short_description = 'Habilitar como nodo federador'

    disable = switch('enabled', False)
    disable.short_description = 'Inhabilitar federacion del nodo'

    def federate(self, _, queryset):
        for harvesting_node in queryset:
            task = FederationTask.objects.create(harvesting_node=harvesting_node)
            portal_url = harvesting_node.url
            apikey = harvesting_node.apikey
            federate_catalogs.delay(portal_url, apikey, task.pk)
    federate.short_description = 'Correr federacion'


class FederationAdmin(AbstractTaskAdmin):
    readonly_fields = ('created', 'logs',)
    exclude = ('status', 'finished',)
    list_display = ('__unicode__',)

    model = FederationTask
    task = federation_run
    callable_str = 'monitoreo.apps.dashboard.tasks.federation_run'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('harvesting_node',)
        else:
            return self.readonly_fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "harvesting_node":
            kwargs["queryset"] = HarvestingNode.objects.filter(enabled=True)
        return super(FederationAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super(FederationAdmin, self).save_model(request, obj, form, change)
        federate_catalogs.delay(obj.harvesting_node.url,
                                obj.harvesting_node.apikey,
                                obj.pk)


class IndicatorTaskAdmin(AbstractTaskAdmin):
    readonly_fields = ('created', 'logs', 'status', 'finished')
    list_display = ('__unicode__',)

    model = IndicatorsGenerationTask
    task = generate_indicators
    callable_str = 'monitoreo.apps.dashboard.indicators_tasks.indicators_run'


class ReportAdmin(AbstractTaskAdmin):
    readonly_fields = ('created', 'logs', 'status', 'finished')
    list_display = ('__unicode__',)

    model = ReportGenerationTask
    task = send_reports
    callable_str = 'monitoreo.apps.dashboard.report_tasks.'


admin.site.register(ReportGenerationTask, ReportAdmin)
admin.site.register(FederationTask, FederationAdmin)
admin.site.register(IndicatorsGenerationTask, IndicatorTaskAdmin)
admin.site.register(HarvestingNode, HarvestingNodeAdmin)
admin.site.register(Indicador, IndicatorAdmin)
admin.site.register(IndicadorRed, IndicatorRedAdmin)
admin.site.register(IndicatorType, IndicatorTypeAdmin)
admin.site.register(TableColumn, TableColumnAdmin)
