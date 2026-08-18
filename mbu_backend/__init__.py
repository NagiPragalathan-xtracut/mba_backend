"""
Project package.

Django's first-choice MySQL driver is `mysqlclient`, a C extension that links
against the MySQL client library. Several hosts - Vercel's build image among
them - ship no MySQL headers, so the wheel cannot be built there and `pip
install` fails outright.

`PyMySQL` is a pure-Python implementation of the same protocol that installs
anywhere. It registers itself under the `MySQLdb` name Django looks for, and
reports a version high enough to satisfy Django's minimum-driver check.

mysqlclient is preferred when it is present (it is faster); PyMySQL is used
only as the fallback. `USING_PYMYSQL` tells the settings module which one won,
because the two drivers spell their TLS options differently.
"""

try:  # pragma: no cover - depends on which driver the host could install
    import MySQLdb  # noqa: F401  - the C driver, preferred when available

    USING_PYMYSQL = False
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
        USING_PYMYSQL = True
    except ImportError:
        # Neither driver is installed. That is fine on SQLite; Django raises a
        # clear error of its own if a MySQL connection is actually attempted.
        USING_PYMYSQL = False
