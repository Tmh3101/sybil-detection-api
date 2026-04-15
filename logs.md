INFO: Loaded rf_model from data/random_forest_gat.pkl
INFO: AI Models loaded.
INFO: Application startup complete.
INFO: Using local credentials file: .creds/service-account-key.json
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/google/cloud/bigquery/table.py:1994: UserWarning: BigQuery Storage module not found, fetch data with the REST endpoint instead.
warnings.warn(
INFO: --- [NODE VERIFICATION: 0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec] ---
INFO: 1. Info: Handle='byd_global', OwnedBy='0x53acd90d59e5da72463eacbcbbd429a7c1780c75', HasAvatar=Yes
INFO: {'profile_id': '0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec', 'handle': 'byd_global', 'display_name': 'BYD Global', 'picture_url': 'https://media.orbapi.xyz/thumbnailDimension768/https://ik.imagekit.io/lens/b98b94c8d5420e4f3248b8bc12cb272b2236575c6cfe4d24e0a1b7efe3f5c491_GuoE7BNos.webp', 'owned_by': '0x53acd90d59e5da72463eacbcbbd429a7c1780c75', 'bio': 'BYD is a global leader in electric vehicles, battery innovation, and sustainable energy solutions. Advancing zero‑emission mobility worldwide, we’re excited to announce a giveaway of a brand‑new BYD EV! 🚗⚡🌍', 'created_on': Timestamp('2026-01-08 08:17:23.475870+0000', tz='UTC'), 'trust_score': 16.5, 'total_posts': 4, 'total_comments': 0, 'total_reposts': 0, 'total_collects': 0, 'total_tips': 0, 'total_quotes': 0, 'total_reacted': 4, 'total_reactions': 4, 'total_followers': 0, 'total_following': 18}
INFO: 2. Stats: TrustScore=16.5, Posts=4, Followers=0, Following=18
INFO: ========== BẮT ĐẦU FALLBACK PIPELINE CHO 0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec ==========
INFO: [GRAPH STATE] Hiện có 4997 nodes trong RAM.
INFO: [BIGQUERY EDGES] Kéo về 22 raw edges từ BigQuery.
INFO: [PHYSICAL EDGES SUMMARY] Đã nối: 8 edges. Bỏ qua (ngoài RAM): 14 edges.
INFO: [CO-OWNER SUMMARY] candidates=0, undirected_pairs_added=0, directed_edges_added=0
INFO: Loading SentenceTransformer model 'all-MiniLM-L6-v2'...
INFO: Load pretrained SentenceTransformer: all-MiniLM-L6-v2

INFO: [SIMILARITY SUMMARY] candidates=4997, undirected_pairs_added=0, skipped_by_2of3=4997, directed_edges_added=0
INFO: --- [EDGES VERIFICATION: 0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec] ---
INFO: Tổng số Edges kết nối: outgoing=12, incoming=12, combined=24
INFO: Thống kê theo Tầng (Layers):
INFO: - Follow Layer (Directed): 8 edges
INFO: - Interact Layer (Directed): 16 edges
INFO: Chi tiết theo Loại (Types):
INFO: - [FOLLOW] (Weight: 1.0): 4 edges
INFO: - [UPVOTE] (Weight: 1.0): 8 edges
INFO: - [UPVOTE_REV] (Weight: 0.5): 8 edges
INFO: - [FOLLOW_REV] (Weight: 0.5): 4 edges
INFO: ========== KẾT THÚC FALLBACK PIPELINE ==========

INFO: 127.0.0.1:55996 - "GET /api/v1/inspector/profile/0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec HTTP/1.1" 200 OK
Batches: 100%|██████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 3.97it/s]
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/sklearn/utils/validation.py:2742: UserWarning: X has feature names, but StandardScaler was fitted without feature names
warnings.warn(
INFO: 127.0.0.1:33702 - "GET /api/v1/inspector/profile/0xbdf6e40ab4b632e83aa3dd9c8a03ebfd034b4cec HTTP/1.1" 200 OK
INFO: Using local credentials file: .creds/service-account-key.json
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/google/cloud/bigquery/table.py:1994: UserWarning: BigQuery Storage module not found, fetch data with the REST endpoint instead.
warnings.warn(
INFO: --- [NODE VERIFICATION: 0x4a2248b60200684a4a25a6f799674a2ef5a068db] ---
INFO: 1. Info: Handle='criptid_i', OwnedBy='0xdbd2608cd98302994700c08fb2b08c564e9fd140', HasAvatar=No
INFO: {'profile_id': '0x4a2248b60200684a4a25a6f799674a2ef5a068db', 'handle': 'criptid_i', 'display_name': 'criptid_i', 'picture_url': '', 'owned_by': '0xdbd2608cd98302994700c08fb2b08c564e9fd140', 'bio': '', 'created_on': Timestamp('2026-01-03 00:47:56.964722+0000', tz='UTC'), 'trust_score': 1.33, 'total_posts': 1, 'total_comments': 0, 'total_reposts': 0, 'total_collects': 0, 'total_tips': 0, 'total_quotes': 0, 'total_reacted': 0, 'total_reactions': 0, 'total_followers': 0, 'total_following': 0}
INFO: 2. Stats: TrustScore=1.33, Posts=1, Followers=0, Following=0
INFO: ========== BẮT ĐẦU FALLBACK PIPELINE CHO 0x4a2248b60200684a4a25a6f799674a2ef5a068db ==========
INFO: [GRAPH STATE] Hiện có 4998 nodes trong RAM.
INFO: [CO-OWNER SUMMARY] candidates=0, undirected_pairs_added=0, directed_edges_added=0
INFO: [SIMILARITY SUMMARY] candidates=4998, undirected_pairs_added=0, skipped_by_2of3=4998, directed_edges_added=0
INFO: --- [EDGES VERIFICATION: 0x4a2248b60200684a4a25a6f799674a2ef5a068db] ---
INFO: Tổng số Edges kết nối: outgoing=0, incoming=0, combined=0
INFO: Thống kê theo Tầng (Layers):
INFO: Chi tiết theo Loại (Types):
INFO: ========== KẾT THÚC FALLBACK PIPELINE ==========
Batches: 100%|██████████████████████████████████████████████████████████████████████████| 1/1 [00:00<00:00, 40.55it/s]
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/sklearn/utils/validation.py:2742: UserWarning: X has feature names, but StandardScaler was fitted without feature names
warnings.warn(
INFO: 127.0.0.1:40150 - "GET /api/v1/inspector/profile/0x4a2248b60200684a4a25a6f799674a2ef5a068db HTTP/1.1" 200 OK
INFO: Using local credentials file: .creds/service-account-key.json
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/google/cloud/bigquery/table.py:1994: UserWarning: BigQuery Storage module not found, fetch data with the REST endpoint instead.
warnings.warn(
INFO: --- [NODE VERIFICATION: 0x1a9eaed98128eae899c605e5a12850811f23c137] ---
INFO: 1. Info: Handle='aizen021712', OwnedBy='0x9b4bfc1bb69fd764646651bc9cb5982f6f1994a7', HasAvatar=No
INFO: {'profile_id': '0x1a9eaed98128eae899c605e5a12850811f23c137', 'handle': 'aizen021712', 'display_name': 'aizen021712', 'picture_url': '', 'owned_by': '0x9b4bfc1bb69fd764646651bc9cb5982f6f1994a7', 'bio': '', 'created_on': Timestamp('2026-01-13 05:33:45.991752+0000', tz='UTC'), 'trust_score': 0.27, 'total_posts': 1, 'total_comments': 0, 'total_reposts': 0, 'total_collects': 0, 'total_tips': 0, 'total_quotes': 0, 'total_reacted': 0, 'total_reactions': 0, 'total_followers': 0, 'total_following': 20}
INFO: 2. Stats: TrustScore=0.27, Posts=1, Followers=0, Following=20
INFO: ========== BẮT ĐẦU FALLBACK PIPELINE CHO 0x1a9eaed98128eae899c605e5a12850811f23c137 ==========
INFO: [GRAPH STATE] Hiện có 4999 nodes trong RAM.
INFO: [BIGQUERY EDGES] Kéo về 20 raw edges từ BigQuery.
INFO: [PHYSICAL EDGES SUMMARY] Đã nối: 6 edges. Bỏ qua (ngoài RAM): 14 edges.
INFO: [CO-OWNER SUMMARY] candidates=0, undirected_pairs_added=0, directed_edges_added=0
INFO: [SIMILARITY SUMMARY] candidates=4999, undirected_pairs_added=0, skipped_by_2of3=4999, directed_edges_added=0
INFO: --- [EDGES VERIFICATION: 0x1a9eaed98128eae899c605e5a12850811f23c137] ---
INFO: Tổng số Edges kết nối: outgoing=6, incoming=6, combined=12
INFO: Thống kê theo Tầng (Layers):
INFO: - Follow Layer (Directed): 12 edges
INFO: Chi tiết theo Loại (Types):
INFO: - [FOLLOW] (Weight: 1.0): 6 edges
INFO: - [FOLLOW_REV] (Weight: 0.5): 6 edges
INFO: ========== KẾT THÚC FALLBACK PIPELINE ==========
Batches: 100%|████████████████████████████████████████████████████████████████████████| 44/44 [00:06<00:00, 6.77it/s]
/home/tmh3101/.conda/envs/sybil_detection_app/lib/python3.10/site-packages/sklearn/utils/validation.py:2742: UserWarning: X has feature names, but StandardScaler was fitted without feature names
warnings.warn(
INFO: 127.0.0.1:43096 - "GET /api/v1/inspector/profile/0x1a9eaed98128eae899c605e5a12850811f23c137 HTTP/1.1" 200
