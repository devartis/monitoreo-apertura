#! coding: utf-8

import logging
from django_rq import job

from pydatajson.core import DataJson
from pydatajson.federation import harvest_catalog_to_ckan
from django_datajsonar.apps.management.models import Node
from django_datajsonar.apps.api.models import Dataset
from .models import HarvestingNode

logger = logging.getLogger(__name__)


def federation_run():
    harvesting_nodes = HarvestingNode.objects.filter(enabled=True)
    for harvester in harvesting_nodes:
        portal_url = harvester.url
        apikey = harvester.apikey
        federate_catalog(portal_url, apikey)


@job('indexing')
def federate_catalog(portal_url, apikey):
    nodes = Node.objects.filter(indexable=True)
    for node in nodes:
        catalog_id = node.catalog_id
        catalog = DataJson(node.catalog_url)
        catalog.generate_distribution_ids()
        dataset_list = get_dataset_list(node, catalog)
        try:
            harvest_catalog_to_ckan(catalog, portal_url, apikey, catalog_id, dataset_list)
        except Exception as e:
            logger.error(u"Error federando catalog: %s datasets: %s - Error: %s" %
                         (catalog_id, dataset_list, e))


def get_dataset_list(node, catalog):
    catalog_report = catalog.validate_catalog()
    valid_datasets = [ds['identifier'] for ds in catalog_report['error']['dataset'] if ds['status'] == 'OK']
    return list(Dataset.objects.filter(catalog__identifier=node.catalog_id, indexable=True,
                                       identifier__in=valid_datasets).values_list("identifier", flat=True))