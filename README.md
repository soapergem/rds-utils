# RDS Utilities

This is a simple utility library providing some helpful functions for interacting with RDS.
Specifically, these functions are useful when utilizing the [RDS Data API]. The RDS Data API
allows you to connect to an RDS instance directly using the AWS SDK without needing any
additional database drivers or libraries (such as psycopg2). I found that the syntax for
utilizing [the RDS Data API within boto3] was not entirely intuitive so I made these
wrapper functions to make adoption of this API a little easier. This library is also
meant to serve as reference material for my blog post on Python fundamentals and how
publishing libraries works. But I hope the functions can be at least nominally useful to some.

## Available Functions

Currently, there are four utility functions exposed through this library:

* execute_query
* fetch_query
* format_parameters
* get_xacct_session

Here is what each function does:

**execute_query(session, rds_endpoint_arn, secret_arn, database, query, parameters):**
Executes a query against the specified RDS instance. All arguments except `parameters`
are required. It does not matter whether the query returns a result set or not. This
function returns the raw response from boto3's [execute_sql] function, as this function
is a wrapper for that command. As such, there may be keys named `records` and
`numberOfRecordsUpdated`. Note that the top level `sqlStatementResults` is not present
because we pass in `includeResultMetadata=True` to the underlying function.

* `session` is a instance of a boto3 session
* `rds_endpoint_arn` is a string identifying the particular RDS cluster
* `secret_arn` is a string identifying an AWS Secrets Manager secret containing valid database credentials
* `database` is the name of the database within the RDS cluster to target
* `query` is a string containing the SQL query you wish to execute
* `parameters` is an optional dictionary of parameters to pass into the query

For example, if your query is `SELECT * FROM employees WHERE employee_id = :id LIMIT 1`, you
might set the value of `parameters` to something like `{"id": 1}`.

**fetch_query(session, rds_endpoint_arn, secret_arn, database, query, parameters):**
Similar to the `execute_query` function, except this function expects a result set
(in other words, this is useful for SELECT queries but not for INSERT or UPDATE queries).
The function also reformats the output into a clean list of rows (instead of the raw boto3 response).
It will collapse nested keys like `stringValue` or `doubleValue` in the response and
utilize the column names as dictionary keys on each row.

In other words, if you pass in a query like this: `SELECT employee_id, name, title FROM employees LIMIT 3`
then you might get a response like this:

```json
[
    {"employee_id": 1, "name": "Alice", "title": "Senior Engineer"},
    {"employee_id": 2, "name": "Bob", "title": "Junior Engineer"},
    {"employee_id": 3, "name": "Sam", "title": "Manager"}
]
```

**format_parameters(parameters):** Transforms a dictionary of parameters into the format
which boto3 utilizes when calling its underlying functions. For instance, if you pass in
a value like `{"id": 1, "name": "Alice"}` the output of this function will be as follows:

```json
[
    {
        "name": "id",
        "value": {"doubleValue": 1}
    },
    {
        "name": "name",
        "value": {"stringValue": "Alice"}
    }
]
```

This function is automatically invoked by both `execute_query` and `fetch_query` so you
should not need to call it directly. It is exposed nonetheless.

**get_xacct_session(session, assume_role_arn):** Instantiates a boto3 service within a
secondary AWS account using assume-role. This is useful when an application living in
one AWS account needs to access an RDS instance living in a separate AWS account. This
of course requires that you set up the appropriate IAM roles in both accounts first.
Here is an example of how you might use this:

```python
import os
import boto3
from rds_utils import fetch_query, get_xacct_session

session1 = boto3.Session(profile_name="account_a", region_name="us-east-1")
session2 = get_xacct_session(session1, "arn:aws:iam::123456789012:role/account_b_rds_role")
results = fetch_query(
    session2,
    os.getenv("RDS_ENDPOINT_ARN"),
    os.getenv("RDS_SECRET_ARN"),
    os.getenv("RDS_DATABASE_NAME"),
    "SELECT * FROM employees WHERE employee_id = :id",
    {"id": 1},
)
print(results)
```


[RDS Data API]: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html
[the RDS Data API within boto3]: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds-data.html
[execute_sql]: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds-data/client/execute_sql.html