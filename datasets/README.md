# Datasets

## `london_real.npz` — Low Carbon London smart-meter consumption

A 10-home, 14-day slice of **real** residential electricity consumption from the
Low Carbon London smart-meter trial (UK Power Networks), taken from the Hugging Face
mirror [`eeJunCao/London_smart_meter`](https://huggingface.co/datasets/eeJunCao/London_smart_meter).

The trial published **half-hourly kWh** readings per household. To match EnerGPT's
engine, which works in **hourly watt-hours**, each pair of half-hourly readings is
summed and converted to integer Wh (`kWh * 1000`, rounded). The vendored file holds:

| Key         | Shape      | Meaning                                        |
| ----------- | ---------- | ---------------------------------------------- |
| `readings`  | `(10, 336)`| hourly watt-hours, 10 homes × 14 days × 24 h   |
| `item_ids`  | `(10,)`    | the trial's household ids (e.g. `MAC000002`)   |

Only homes with a complete, non-negative 14-day stretch were kept. Across the 10
homes the readings span ~55–6500 Wh/hour, with the evening peak (19:00–21:00) that
residential demand classically shows.

### Regenerating

```bash
python -c "from energpt.real_data import fetch_london; print(fetch_london())"
```

This re-downloads the subset from the Hugging Face datasets-server and rewrites
`london_real.npz`. It needs outbound access to `datasets-server.huggingface.co`.

### How it is used

`energpt.real_data.load_london()` loads the homes, and `python -m energpt.real_benchmark`
runs the deterministic analysis engine and the offline advisor over all of them —
see the "Validated on real consumption" section of the top-level README.

The licence and terms of the original Low Carbon London data apply; this subset is
vendored for reproducible benchmarking only.
