from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime

# App Insights
# TODO: Import required libraries for App Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

# For metrics
stats = stats_module.stats
view_manager = stats.view_manager
app = Flask(__name__)
# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')
inst_key = 'InstrumentationKey=f5aa29d6-f564-4ca2-b477-1c6956ff22a0;'


# Logging
logger = logging.getLogger(__name__) # TODO: Setup logger
logger.addHandler(AzureLogHandler(connection_string=inst_key))
logger.setLevel(logging.INFO) #set the logging level
logger.info("logger set up successfully")
logger.info("app_insights_instrumentation_key = {}".format(inst_key))

# Metrics
exporter = metrics_exporter.new_metrics_exporter(
    enable_standard_metrics=True,
    connection_string=inst_key) # TODO: Setup exporter
view_manager.register_exporter(exporter)
logger.info("metrics set up successfully")

# Tracing
tracer = Tracer(
    exporter=AzureExporter(
        connection_string=inst_key),
        sampler=ProbabilitySampler(1.0),
)# TODO: Setup tracer

logger.info("tracer set up successfully")


# Requests
middleware = FlaskMiddleware(
 app,
 exporter=AzureExporter(connection_string=inst_key),
 sampler=ProbabilitySampler(rate=1.0)
)# TODO: Setup flask middleware
logger.info("requests set up successfully")
logger.warning("**********setup completed**********")


if ("VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']):
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if ("VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']):
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if ("TITLE" in os.environ and os.environ['TITLE']):
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1,0)
if not r.get(button2): r.set(button2,0)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':

        # Get current values
        vote1 = r.get(button1).decode('utf-8')
        # TODO: use tracer object to trace cat vote
        tracer.span(name="Voted: Cats")
        vote2 = r.get(button2).decode('utf-8')
        # TODO: use tracer object to trace dog vote
        tracer.span(name="Voted: Dogs")

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':

        if request.form['vote'] == 'reset':

            # Empty table and return results
            r.set(button1,0)
            r.set(button2,0)
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            # TODO: use logger object to log cat vote
            logger.warning('Cats', extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            # TODO: use logger object to log dog vote
            logger.warning('Dogs', extra=properties)

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:

            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote,1)

            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # comment line below when deploying to VMSS
    # app.run() # local
    # uncomment the line below before deployment to VMSS
    app.run(host='0.0.0.0', threaded=True, debug=True) # remote
    