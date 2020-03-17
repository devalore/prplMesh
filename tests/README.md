This directory contains the end-to-end tests of prplMesh

TODO fill in the details.

## Description of tests

### ap_config_renew

- send 0x0006 + 0x0001 + 2x 0x0001 (1905 Topology Notification message) to Gateway
- check log wlan0 received credentials SSID 1 bss_type 2
- check log wlan0 received credentials SSID 2 bss_type 1
- check log wlan2 tear down radio

### ap_config_bss_tear_down
- send 0x0006 (1905 Topology Notification message) to repeater 1 as Gateway
- sleep 3
- check log repeater 1 wlan0 received credentials SSID 3 bss_type 2
- check log repeater 1 wlan2 tear down radio
- send 0x0006 (1905 Topology Notification message) to repeater 1 as Gateway
- check log repeater 1 wlan2 tear down radio

### channel_selection
- send 0x8004 (Channel Preference Query message) to repeater 1 as Gateway
- check log repeater 1 wlan0 message CHANNEL_PREFERENCE_QUERY_MESSAGE received
- check log repeater 1 wlan2 message CHANNEL_PREFERENCE_QUERY_MESSAGE received
- send 0x8006 (Channel Selection Request message) to repeater 1 as Gateway
- check log repeater 1 wlan0 message CHANNEL_SELECTION_REQUEST_MESSAGE received
- check log repeater 1 wlan2 message CHANNEL_SELECTION_REQUEST_MESSAGE received

### ap_capability_query
- send 0x8001 (AP Capability Query message) to repeater 1 as Gateway
- check log repeater 1 agent message AP_CAPABILITY_QUERY_MESSAGE received
- check log controller AP_CAPABILITY_REPORT_MESSAGE received

### combined_infra_metrics
- send 0x800B (AP Metrics Query Message) + 0x0007 (AP- Autoconfiguration Search message) to repeater 1 as Gateway
- check log repeater 1 wlan0 AP_METRICS_QUERY_MESSAGE message received
- send 0x800C (AP Metrics Response message) as Repeater 1 to Gateway
- check log controller AP_METRICS_RESPONSE_MESSAGE received
- send 0x800B (AP Metrics Query Message) + 0x0007 (AP- Autoconfiguration Search message) to repeater 2 as Gateway
- check log repeater 2 wlan2 message AP_METRICS_QUERY_MESSAGE received
- send 0x800C (AP Metrics Response message) as Repeater 2 to Gateway
- check log controller AP_METRICS_RESPONSE_MESSAGE received
- send 0x0005 to repeater 1 as Gateway
- check logs repeater 1 wlan0 Received LINK_METRIC_QUERY_MESSAGE
- send 0x0006 to Gateway as repeater 1
- check logs controller Received LINK_METRIC_RESPONSE_MESSAGE
- send 0x8013 (Combined Infrastructure Metrics message) to repeater 1 as Gateway
- check logs repeater 1 agent Received COMBINED_INFRASTRUCTURE_METRICS
- check logs repeater 1 agent Received TLV_TRANSMITTER_LINK_METRIC
- check logs repeater 1 agent Received TLV_RECEIVER_LINK_METRIC

### ...

## Mapping of certification tests

Flow tests between parenthesis don't fully cover the certification test.
In addition, many certification tests include a configuration phase which is not covered in the flow test.

| Certification test | test flow |
| ------------------ | --------- |
| 4.2.1 MAUT §5 Multi-AP Ethernet Onboarding and Initialization test | (channel_selection)
| 4.2.2 MAUT §5.1/§5.2 Multi-AP Wi-Fi Onboarding and Initialization test 1 |
| 4.2.3 MAUT §5.1/§5.2 Multi-AP Wi-Fi Onboarding and Initialization test 2 |
| 4.3.1 MAUT §6.2 Supported Services Discovery test |
| 4.3.2 MAUT §6.2/§6.3 Client association and disassociation test | (client_association_dummy) (client_association)
| 4.4.1 MAUT §7.1/§7.2 Initial AP configuration test | (client_association_dummy)
| 4.4.2 MAUT §7.1/§7.2 AP configuration renew test | (ap_config_renew) (ap_config_bss_tear_down)
| 4.4.3 MAUT §7.1/§7.Two AP configuration BSS Tear Down test | (ap_config_bss_tear_down)
| 4.5.1 MAUT §8.1 Channel Preference Query test | (channel_selection)
| 4.5.2 MAUT §8.2 Channel Selection Request Message test |
| 4.5.3 MAUT §8.1 DFS Status update report test |
| 4.6.1 MAUT §9.1 AP capability report test | (ap_capability_query)
| 4.6.2 MAUT §9.2 Client capability reporting test | (client_capability_query)
| 4.6.3 MAUT §9.2 Client capability query transmit test |
| 4.7.1 MAUT §10.1 Backhaul Link Metric Query test - All Neighbors |
| 4.7.2 MAUT §10.1 Backhaul Wi-Fi Link Metric Query test - Specific Neighbor |
| 4.7.3 MAUT §10.1 Backhaul Ethernet Link Metric Query test - Specific Neighbor |
| 4.7.4 MAUT §10.2 Per-AP Link Metrics Query Message test | (combined_infra_metrics)
| 4.7.5 MAUT §10.2 Per-AP Metrics Response Message Controlled by AP Metrics Reporting Interval test |
| 4.7.6 MAUT §10.2 Per-AP Metrics Response Controlled by AP Metrics Channel Utilization Reporting Threshold test |
| 4.7.7 MAUT §10.3.1 Associated STA Link Metrics and Counters test |
| 4.7.8 MAUT §10.3.2 Un-Associated STA RSSI Measurements test |
| 4.7.9 MAUT §10.3.3 Beacon Report Query and Response test |
| 4.8.1 MAUT §11.1 BTM-based Client Steering Mandate test | (client_steering_mandate) (client_steering_dummy)
| 4.8.2 MAUT §11.1 Legacy Client Steering Mandate test | (client_steering_policy)
| 4.8.3 MAUT §11.2 Client Steering Opportunity test |
| 4.8.4 MAUT §11.3.1 RCPI Policy-based Steering test |
| 4.8.5 MAUT §11.6 Client Association Control test |
| 4.9.1 MAUT §12 Backhaul STA Steering Request test |
| 4.10.1 MAUT §14 Data Passing test 1 (one-hop with MAUT connected to the CTT Agent) |
| 4.10.2 MAUT §14 Data Passing test 2 (two-hop with MAUT connected to an Agent) |
| 4.10.3 MAUT §14 Data Passing test 3 (one-hop with CTT Agent connected to MAUT) |
| 4.10.4 MAUT §14 Data Passing test 4 (two-hop with CTT Agent connected to MAUT) |
| 4.10.5 MAUT §14 Data Passing test 5 (with MAUT between CTT Agent1 and CTT Agent 2) |
| 4.10.6 MAUT §14 Data Passing test 6 (with a CTT STA connected to MAUT) |
| 4.11.1 MAUT §15 Multi-AP Control Messaging Reliability test |
| 4.12.1 MAUT §16 Higher layer data payload over 1905 trigger test | (higher_layer_data_payload_trigger)
| 4.12.2 MAUT §16 Higher layer data payload over 1905 test |
| 5.3.1 MCUT §6.1/§6.2 Supported Services Discovery test |
| 5.4.1 MCUT §7.1/§7.2 Initial AP configuration test | (client_association_dummy) (client_association)
| 5.4.2 MCUT §7.1/§7.2 AP configuration renew test | ap_config_renew
| 5.4.3 MCUT §7.1/§7.2 AP configuration BSS Tear Down test | ap_config_bss_tear_down
| 5.5.1 MCUT §8 Channel Preference Query and Channel Selection Request Message test | (channel_selection)
| 5.6.1 MCUT §9.1 AP capability query test | (ap_capability_query)
| 5.6.2 MCUT §9.2 Client capability query test | (client_capability_query)
| 5.7.1 MCUT §10.4 Combined Infrastructure Metrics test | (combined_infra_metrics)
| 5.8.1 MCUT §11 Client Steering for Steering Mandate and Steering Opportunity test | (client_steering_mandate) (client_steering_dummy)
| 5.8.2 MCUT §11 Setting Client Steering Policy test | (client_steering_policy)
| 5.8.3 MCUT §11 Client Association Control Message test |
| 5.10.1 MCUT §16 Higher layer data payload over 1905 trigger test | (higher_layer_data_payload_trigger)
| 5.10.2 MCUT §16 Higher layer data payload over 1905 test |
|
