"""SRPM metadata caching service"""
import sarge

from flask import Flask
application = Flask(__name__)

@application.route("/")
def check_builder():
    # No real code yet, just checking repdevtools is available
    return sarge.get_stdout(["rpm2cpio", "--help"])

if __name__ == "__main__":
    application.run()
