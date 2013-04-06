# -*- coding: utf-8 -*-
from apptools.pipelines import BasePipeline


## ContentPipeline
# Base pipeline class for dynamic content.
class ContentPipeline(BasePipeline): pass


## ContentAreaPipeline
# Operates on ContentArea entities.
class ContentAreaPipeline(ContentPipeline): pass


## ContentSnippetPipeline
# Operates on ContentSnippet entities.
class ContentSnippetPipeline(ContentPipeline): pass


## ContentSummaryPipeline
# Operates on ContentSummary entities.
class ContentSummaryPipeline(ContentPipeline): pass
