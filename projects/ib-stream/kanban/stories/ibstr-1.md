# ibstr-1: IB-Studies V3 API Upgrade

Upgrade ib-studies to support the new v3 optimized API from ib-stream, adding historical data range queries and ensuring compatibility with the v3 storage optimization system.

## Description

This story involves upgrading the ib-studies client application to support the v3 optimized API and storage system implemented in ib-stream. The upgrade includes fixing current v2 compatibility issues, adding v3 protocol support, and implementing historical data analysis capabilities using the new storage optimization features.

## Git Configuration

- **Repository**: https://github.com/lakowske/ib-stream.git
- **Branch From**: main
- **Merge To**: main
- **Feature Branch**: ibstr-1-studies-v3-upgrade
- **Component**: ib-studies client package

## Story Requirements

- Fix critical v2 API endpoint compatibility issues preventing current functionality
- Implement v3 client support to leverage 65% storage efficiency improvements
- Add historical data analysis using v3 time-range queries with hour-based granularity
- Maintain backward compatibility with existing v2 workflows
- Add comprehensive testing against running ib-stream server with v3 support
- Update CLI interface for protocol selection and historical analysis
- Ensure data integrity consistency between v2 and v3 protocols

## Acceptance Criteria

- [ ] v2 API compatibility fixed - all existing commands functional
- [ ] v3 live streaming client implemented with optimized message format
- [ ] Historical analysis features using v3 `/buffer/{contract_id}/query` endpoints
- [ ] Protocol selection via `--protocol v2|v3` CLI option
- [ ] Historical time-range analysis with `--start-time` and `--end-time` options
- [ ] Data consistency validated between v2 and v3 protocols
- [ ] Performance improvements measurable (2-3x faster historical queries)
- [ ] Integration tests passing against v3-enabled ib-stream server
- [ ] Documentation updated with v3 examples and migration guide
- [ ] All existing tests continue to pass
- [ ] Ready for merge to main branch

## Technical Notes

**Current Issues**:
- ib-studies expects `/v2/stream/{contract_id}` but ib-stream provides `/v2/stream/{contract_id}/live`
- No support for v3 optimized message format (ts, st, cid, tt, rid field names)
- Missing historical analysis capabilities

**Key Implementation Areas**:
- Update `stream_client.py` for correct v2 endpoint usage
- Create `V3StreamClient` and `V3HistoricalClient` classes
- Add v3 message format parsing and normalization
- Implement historical analysis commands and CLI options
- Add protocol version abstraction layer for studies

**Performance Targets**:
- Leverage v3's 65% storage efficiency for faster historical queries
- Support hour-based file granularity for optimized range queries
- Maintain sub-second response times for typical analysis windows

## Dependencies

- ib-stream server running with v3 storage optimization
- Historical data available in v3 format (624K+ messages/hour tested)
- Active IB Gateway connection for live streaming validation

## Test Data

- Use MNQ contract (711280073) with existing v3 historical data
- Test against hour 17 data (2025-08-01T17:00:00Z) with 624K+ messages
- Validate against both v2 and v3 storage formats for consistency

## Linked Implementation

This story builds on the completed storage optimization v3 implementation and leverages the existing v3 API endpoints and optimized storage system.