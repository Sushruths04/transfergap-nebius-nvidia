# cluster_pipeline_pexels_refused_v1

Negative control: an internet clip (Pexels packing box) through RTMW3D. The pipeline stops at the demo stage with
"hand path extent [5.87, 0.63, 4.43] m exceeds 1.5 m" and does not simulate it. This is the intended behaviour (RTMW3D failed on internet clips in
`../pose_estimator_bakeoff_v3`); later stages are reported as skipped.
