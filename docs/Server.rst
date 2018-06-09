Running a Server
================

PDSC currently supports two methods for querying observations: local queries and
remote queries to a server over HTTP. The :py:mod:`pdsc` package provides a
command-line tool for running the server. It can be started as follows::

    $ pdsc_server -d /path/to/index/files --port [port] --socket_host [0.0.0.0]

If no arguments are specified, the server will use the ``PDSC_DATABASE_DIR``
environment variable to determine the location of the index files. The defaul
port is ``7372`` ("P-D-S-C" on a numeric keypad), and the default socket host is
``0.0.0.0`` (serve to all IP addresses).

The :ref:`Environment Variables` section describes how to set environment
variables that will allow Python clients to automaticaly identify the location
and port of the PDSC server.

.. Warning::
    The PDSC server is not yet designed to be robust against malicious queries.
    While some care has been taken to properly parse arguments to avoid SQL
    injection attacks, for example, a thorough review of potential security
    vulnerabilities has not yet been performed.
