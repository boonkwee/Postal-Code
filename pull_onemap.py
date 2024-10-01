import requests
import json
import time
from settings import ONEMAP_KEY
from database import session_pool
from models import Location
from models import PostalCode
from api import Api
# from IPython.display import Markdown, display
headers = {"Authorization": ONEMAP_KEY}

url = "https://www.onemap.gov.sg/api/common/elastic/search"

params = {
    'searchVal'     : "000001",
    'returnGeom'    : "Y",
    'getAddrDetails': "N",
    'pageNum'       : "1"
}

if __name__=='__main__':
  api = Api(url=url, method='GET', param=params)
  # insert new locations record
  start_time = time.time()
  char_count = 0
  counter = 0

  for j in range(1, 1001):
    for i in range(1, 100):
      # wait_some_seconds()   # Throttling effect
      postal_code = f"{i:02d}{j:04d}"
      api.set('searchVal', postal_code)
      response = api.call()
      try:
        r = json.loads(response.text)
      except json.JSONDecodeError as e:
        print(f"{str(e)}: [{response.text}]")
        continue
      r = json.loads(response.text)
      if r['found']:
        for index, row in enumerate(r['results']):
          # Create a session from the sessionmaker
          with session_pool() as session:
            # Query for the location where postal_code, page_number and name matches DB
            existing_records = session.query(Location).filter(
                Location.postal_code==postal_code,
                Location.page_number==index+1,
                Location.name==row['SEARCHVAL']).all()
            if existing_records:
              record = existing_records[0]
              display_str = f"{params['searchVal']} | {record.page_number:2d} | {record.total_pages:2d} | {record.record_index:2d} | {record.total_records:2d} | [{record.latitude:1.12f}] | [{record.longitude:3.10f}] | {record.name}"
              print(display_str)
              char_count += len(display_str)
              continue
            else:
              record_index = (r['pageNum']-1)*10 + index+1
              display_str = f"{params['searchVal']} | {r['pageNum']:2d} | {r['totalNumPages']:2d} | {record_index:2d} | {r['found']:2d} | {row['LATITUDE']:16s} | {row['LONGITUDE']:16s} | {row['SEARCHVAL']}"
              print(display_str)
              char_count += len(display_str)

            counter += 1
            newLocation = Location(name=row['SEARCHVAL'],
                                  latitude=r['results'][index]['LATITUDE'],
                                  longitude=r['results'][index]['LONGITUDE'],
                                  total_pages=r['totalNumPages'],
                                  page_number=r['pageNum'],
                                  total_records=r['found'],
                                  record_index=record_index)
            session.add(newLocation)

            # check if postal code already exist in PostalCode, if not exist insert new Postal code
            postalCode = session.query(PostalCode).filter(PostalCode.postal_code==postal_code).one_or_none()
            if postalCode is None:
              newPostalCode = PostalCode(postal_code=postal_code)
              session.add(newPostalCode)
              newLocation.postal_code_index = newPostalCode
            else:
              newLocation.postal_code_index = postalCode
            session.commit()
      # else:
      #   print(f"{params['searchVal']} | {r['found']:2d} |    |")
  # display(Markdown('---'))
  end_time = time.time()
  hh = int(end_time-start_time) // 3600
  mm = int(end_time-start_time) % 3600 // 60
  ss = int(end_time-start_time) % 60
  record_insertion_speed = counter / (end_time-start_time)

  print(f"{counter} records added; {char_count} characters. ", end='')
  print(f"Duration: {hh:02d}:{mm:02d}:{ss:02d}. Rate: {record_insertion_speed:.3f} records per sec.")
