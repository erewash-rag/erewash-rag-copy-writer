from moto import mock_aws
import pytest
from lambda_function import lambda_handler
import boto3
import responses

def make_event():
    return {
        'erewash_council_news_url': "https://www.erewash.gov.uk/news"
    }

@pytest.fixture
def mock_dynamodb_articles():
    with mock_aws():
        # Set up DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        table = dynamodb.create_table(
            TableName='sources',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )
        table.wait_until_exists()
        # Insert test data
        table.put_item(Item={"id": "https://www.erewash.gov.uk/news/test-article", "sourceId": "erewash_council_news", "content": "The monumental metal structure in Long Eaton was constructed amid the countdown to football’s biggest tournament . . . and appears designed to gladden the hearts of Three Lions fans.But the borough council is stressing that any inspiration it gives to Harry Kane and his men is just a lucky coincidence. The arch spans a stretch of the Erewash Canal – and is actually part of a spectacular new bridge that is taking shape.The crossing at Broad Street is among a string of projects funded by £25million of “Town Deal” investment that the borough council clinched from the government.The crossing is the second of two new ones across the canal that will improve connectivity for local people. The other footbridge and cycle path is at Britannia Mills and will officially be declared open later this month.Local businessman Richard Ledger, who chairs the Long Eaton Town Deal Board, said as work also ramps up on a showcase £10million project to transform the centre of town: “The arch is truly amazing – and if it helps to boost the England team so much the better.“It was a painstaking construction job to put it in place – and gives an indication of just how magnificent the new landmark canal bridge will be. There will also be an entire new waterfront for local people to enjoy.”Excitement is building across the borough ahead of England’s opening World Cup match in North America – where the USA, Canada and Mexico are hosting the finals. The game against Croatia on Wednesday 17 June is in the Texas city of Arlington.Before that fellow finalists Scotland meet Haiti on Sunday 14 June in Boston – in a clash that has an amazing connection to the borough. Ex-Ilkeston Town striker Ché Adams is in the team after helping the Scots thrash Bolivia in a warm-up match. The 29-year-old scored twice in a 4-0 drubbing of the South Americans.", "dateAdded": "2026-06-08", "writtenAbout": False})
        yield

def test_create_article(mock_dynamodb_articles):

    lambda_handler(make_event(), None)
