select store_id, store_name, status, geog
from {{ source('raw', 'stores') }}
