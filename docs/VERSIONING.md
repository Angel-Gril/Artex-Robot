# ARTEX Robot versioning

This repository keeps the application and the Agent SDK as two separately versioned components while shipping a reproducible combined tree.

| Component | Baseline / version | Source |
| --- | --- | --- |
| ARTEX application baseline | original `v0.3.15` (`e6ec56999175509551a1e43a3ee3b053d0941bd9`) | Autumn-27/ARTEX history |
| ARTEX maintenance update | RuoJi6 `v0.3.23` (`620ca5d96c33a417b08fd926e04df1e2b61ffa6d`) | RuoJi6/ARTEX |
| Norma SDK | `v0.4.4` | Go module proxy, copied unchanged into `./norma` |

The root module remains `github.com/Autumn-27/artex`. Its `go.mod` requires `github.com/Autumn-27/norma v0.4.4` and replaces that module with `./norma` for offline and supply-chain-auditable builds. The nested `norma/go.mod` deliberately remains `module github.com/Autumn-27/norma`; it is not renamed to the ARTEX module and can be tagged or exported independently.

Recommended release tags:

- `artex-v0.3.15` — original application baseline;
- `artex-v0.3.23` — application after the RuoJi6 maintenance update;
- `norma-v0.4.4` — the vendored SDK snapshot;
- `v0.3.23-norma.0.4.4` — an optional combined release tag for this repository.

Do not change the nested module path or copy ARTEX code into `norma/`. To update Norma, replace only the nested module from its Go proxy archive, verify its checksum, then run the ARTEX tests with the local `replace` in effect.

## Reproducible checks

```bash
git show artex-v0.3.15:go.mod
git show artex-v0.3.23:go.mod
cat norma/VERSION
go list -m all
go mod verify
go test ./...
```

The Norma `v0.4.4` proxy archive used for this tree has SHA-256:

```text
ECC9456468C0488D833C655E4FBD1565E6DEFD0445D6AF650E6648ECF0CFA357
```

