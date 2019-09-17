# Parameters
# ----------
# db : string
#     Name of the database being queried.
# s3Bucket: string
#     Name of the s3 Bucket for staging results. This bucket will be cleared later.
# query: string
#     SQL query to be fired on the Athena Database

    
def athena_query_to_dataframe(db, s3Bucket, query):
    
    import boto3
    import pandas as pd
    
    client = boto3.client('athena')
    listOfStatus = ['SUCCEEDED', 'FAILED', 'CANCELLED']
    listOfInitialStatus = ['RUNNING', 'QUEUED']
    
    print('Starting Query Execution:')
    
    tempS3Path = 's3://{}'.format(s3Bucket)
    
    response = client.start_query_execution(
        QueryString = query,
        QueryExecutionContext = {
            'Database': db
        },
        ResultConfiguration = {
            'OutputLocation': tempS3Path,
        }
    )

    queryExecutionId = response['QueryExecutionId']

    status = client.get_query_execution(QueryExecutionId = queryExecutionId)['QueryExecution']['Status']['State']

    while status in listOfInitialStatus:
        status = client.get_query_execution(QueryExecutionId = queryExecutionId)['QueryExecution']['Status']['State']
        if status in listOfStatus:
            if status == 'SUCCEEDED':
                print('Query Succeeded!')
                paginator = client.get_paginator('get_query_results')
                query_results = paginator.paginate(
                    QueryExecutionId = queryExecutionId,
                    PaginationConfig = {'PageSize': 1000}
                )
            elif status == 'FAILED':
                print('Query Failed!')
            elif status == 'CANCELLED':
                print('Query Cancelled!')
            break
    
    results = []
    rows = []
    
    print('Processing Response')
    
    for page in query_results:
        for row in page['ResultSet']['Rows']:
            rows.append(row['Data'])

    columns = rows[0]
    rows = rows[1:]

    columns_list = []
    for column in columns:
        columns_list.append(column['VarCharValue'])
        
    print('Creating Dataframe')

    dataframe = pd.DataFrame(columns = columns_list)

    for row in rows:
        df_row = []
        for data in row:
            df_row.append(data['VarCharValue'])
        dataframe.loc[len(dataframe)] = df_row
    
    print('Clearing S3 Bucket')
    
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3Bucket)
    bucket.objects.all().delete()
        
    print('Done!')
    
    return(dataframe)
