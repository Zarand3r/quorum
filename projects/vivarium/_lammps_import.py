"""Convert a LAMMPS micelle-example trajectory into this project's state format.

Stage D0/D1 of the revised ladder: run a known-working open-source model UNCHANGED and score it with
our own metric. This is as much a test of the metric as of the model. If D11's vesicle score cannot
recognise a bilayer that a published, executable reference produces, the metric is still wrong and
nothing it has said about our own runs can be trusted.

The example is 2-D with explicit solvent: 1200 atoms in a 35.86^2 box, of which 150 are amphiphiles
of 3 beads (one head, two tails of different size) and 750 are solvent. Type mapping:

    LAMMPS type 1 -> solvent   (species 0)
    LAMMPS type 2 -> head      (species 1)
    LAMMPS type 3 -> tail      (species 2)
    LAMMPS type 4 -> tail      (species 2)

Our analysis assumes each molecule occupies a contiguous block of `nb` beads with heads first, so
atoms are reordered into that layout using the molecule IDs from the data file. Atom IDs are stable
in LAMMPS, so the data file's id -> molecule map applies to every dump frame.
"""

import sys

import numpy as np

TYPE_TO_SPECIES = {1: 0, 2: 1, 3: 2, 4: 2}


def read_data_topology(path):
    """id -> (molecule, type), from the Atoms section of a LAMMPS data file."""
    out = {}
    with open(path) as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("Atoms")) + 1
    for l in lines[start:]:
        s = l.split()
        if not s:
            continue
        if not s[0].lstrip("-").isdigit():
            break
        out[int(s[0])] = (int(s[1]), int(s[2]))
    return out


def read_dump_frames(path):
    """Yield (timestep, box_length, {id: (x, y)}) for each frame."""
    with open(path) as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        if not lines[i].startswith("ITEM: TIMESTEP"):
            i += 1
            continue
        step = int(lines[i + 1])
        nat = int(lines[i + 3])
        lo, hi = (float(v) for v in lines[i + 5].split()[:2])
        hdr = lines[i + 8].split()[2:]
        ci, cx, cy = hdr.index("id"), hdr.index("x"), hdr.index("y")
        pos = {}
        for k in range(nat):
            s = lines[i + 9 + k].split()
            pos[int(s[ci])] = (float(s[cx]), float(s[cy]))
        yield step, hi - lo, pos
        i += 9 + nat


def convert(data_path, dump_path, out_path, frame=-1):
    topo = read_data_topology(data_path)
    frames = list(read_dump_frames(dump_path))
    step, L, pos = frames[frame]

    mols = {}
    solvent = []
    for aid, (mol, typ) in topo.items():
        if mol == 0:
            solvent.append(aid)
        else:
            mols.setdefault(mol, []).append((typ, aid))
    nb = len(next(iter(mols.values())))
    assert all(len(v) == nb for v in mols.values()), "ragged molecules"
    nh = sum(1 for t, _ in next(iter(mols.values())) if t == 2)

    order = []
    for mol in sorted(mols):
        order += [aid for _, aid in sorted(mols[mol])]     # type order 2,3,4 puts the head first
    order += sorted(solvent)

    x = np.array([pos[a] for a in order], float)
    sp = np.array([TYPE_TO_SPECIES[topo[a][1]] for a in order], int)
    # wrap into the box: LAMMPS dumps unwrapped-in-place coords that can sit slightly outside
    x = np.mod(x, L)
    np.savez_compressed(out_path, x=x, species=sp, L=float(L),
                        n_amph=len(mols), nb=nb, nh=nh)
    print(f"frame t={step}  L={L:.2f}  n_amph={len(mols)}  nb={nb}  nh={nh}  "
          f"solvent={len(solvent)}  -> {out_path}")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2], sys.argv[3],
            int(sys.argv[4]) if len(sys.argv) > 4 else -1)
