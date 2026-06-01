param(
    [string]$VideoDir = "..\CCTV Footage",
    [string]$Out = "data\events.jsonl",
    [int]$Stride = 15,
    [int]$MaxFrames = 0
)

python -m pipeline.detect --video-dir $VideoDir --out $Out --stride $Stride --max-frames $MaxFrames
