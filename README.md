# swamp-api
It's backend API for swamp projects

## Useful URLs
- [Sentry logs](https://swamp.sentry.io/issues/?groupStatsPeriod=auto&project=4505676561317888&query=is%3Aunresolved&sort=freq&statsPeriod=24h)

## Description

## Notes

```
curl "http://localhost:30010/feeds/parse/file"
```

```
curl -X PUT "http://localhost:30010/feeds/parse" \
    -H 'Content-Type: application/json' \
    -d '{"feed_id": 1098, "store_new": true}'
```

```
curl -X PUT "http://localhost:30010/feeds/parse/runner"
```
