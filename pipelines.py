# -*- coding: utf-8 -*-

# Pipeline Imports
try:
	import pipeline
except ImportError:
	logging.critical('GAE lib "Pipelines" is not installed.')
else:

	## BasePipeline
	# This base class provides pipeline utilities.
	class BasePipeline(pipeline.Pipeline):
		pass