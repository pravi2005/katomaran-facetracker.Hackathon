# Face recognition concepts

## Pipeline in this app
face box -> quality gate -> align (5 landmarks, 112x112) -> ArcFace network -> 512-d vector -> L2-normalise -> average 3 -> cosine vs gallery -> threshold.

## ArcFace / InsightFace
ArcFace is a training method (additive angular margin loss) that makes embeddings of the same person cluster tightly on a hypersphere, so *angle* (cosine) is the right distance. InsightFace is the toolkit; `buffalo_l` is a model pack (SCRFD detector + ResNet50 ArcFace trained on WebFace600K, 512-d). Pretrained InsightFace models are for non-commercial research use - mention the licence.

## Why normalise?
After L2 normalisation all vectors have length 1, so `dot(a, b) = cosine`. `FaceMatcher` normalises everything it stores or compares.

## Similarity and threshold
- Metric: cosine similarity, higher = more alike.
- Rule: `similarity >= recognition.similarity_threshold` -> existing person, else register.
- 0.45 is a **starting value**; correct value depends on camera, resolution, lighting, pose. Calibrate: compare same-person pairs vs different-person pairs (`scripts/calibrate_threshold.py`): choose a value between the 5th percentile of same-person scores and the 95th percentile of different-person scores. If they overlap, improve crops instead.
- Too low -> false matches (count too low); too high -> duplicates (count too high).

## Why average several embeddings?
One frame can be blurry or at a bad angle; the mean of 3 good embeddings is more stable, and the quality gate keeps bad frames out. Cost: ENTRY appears about 3 detection cycles after first sight.

## Registration vs recognition
Registration happens only when the best gallery similarity is below the threshold (or the gallery is empty). The database creates the ID; the gallery is updated immediately so the same person can't register twice in a row.

## Known weaknesses (say them yourself)
Twins/lookalikes, masks, extreme angles, low resolution, photos/screens (no liveness detection), identity fixed per track (no re-verification), one embedding per person (no template update), demographic bias of training data, privacy/consent obligations for face data.

## Why not the `face_recognition` library?
The hackathon forbids it; it's dlib-based and older. InsightFace/ArcFace models are stronger and ONNX-based.
