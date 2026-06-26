#!/usr/bin/env python3
"""Convert ELM history NetCDF output to XDMF format on an ATS surface mesh.

Usage:
    elm_to_xdmf.py --run /path/to/run/dir [--domain surface] [--hlevel 0] [--vars VAR1,VAR2,...]

The run directory is expected to contain both the ATS mesh file
(ats_vis_{domain}_mesh.h5) and the ELM history NetCDF files.
Output is written to the same directory.
"""
import argparse
import glob
import os
import re
import sys

import h5py
import netCDF4
import numpy as np


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True,
                   help='Run directory containing ATS mesh h5 and ELM history NetCDF files')
    p.add_argument('--domain', default='surface',
                   help='ATS domain name (default: surface); mesh file is ats_vis_{domain}_mesh.h5')
    p.add_argument('--hlevel', type=int, default=None,
                   help='History level to process (0, 1, 2, ...); default: all found')
    p.add_argument('--vars', default=None,
                   help='Comma-separated ELM variable names to include; default: all surface scalars')
    return p.parse_args()


def get_mesh_info(mesh_path):
    """Return (mesh_cycle_key, n_cells, n_nodes, n_topo)."""
    with h5py.File(mesh_path, 'r') as f:
        cycle_key = list(f.keys())[0]
        n_nodes = f[f'{cycle_key}/Mesh/Nodes'].shape[0]
        n_topo = f[f'{cycle_key}/Mesh/MixedElements'].shape[0]
        if f'{cycle_key}/Mesh/ElementMap' in f:
            n_cells = f[f'{cycle_key}/Mesh/ElementMap'].shape[0]
        else:
            n_cells = None
    return cycle_key, n_cells, n_nodes, n_topo


def find_elm_files(run_dir, hlevel):
    """Return dict mapping hlevel -> sorted list of nc file paths."""
    if hlevel is not None:
        levels = [hlevel]
    else:
        all_files = glob.glob(os.path.join(run_dir, '*.elm.h*.*.nc'))
        levels = sorted({int(re.search(r'\.elm\.h(\d+)\.', f).group(1))
                         for f in all_files
                         if re.search(r'\.elm\.h(\d+)\.', f)})
    result = {}
    for lv in levels:
        files = sorted(glob.glob(os.path.join(run_dir, f'*.elm.h{lv}.*.nc')))
        if files:
            result[lv] = files
    return result


def surface_scalar_vars(nc_file):
    """Return list of variable names with dims (time, lndgrid)."""
    ds = netCDF4.Dataset(nc_file)
    names = [v for v, var in ds.variables.items()
             if var.dimensions == ('time', 'lndgrid')]
    ds.close()
    return names


def elm_time_to_seconds(t_var, tidx):
    """Convert ELM time[tidx] to seconds (float) using the variable's units."""
    days = float(t_var[tidx])
    return days * 86400.0


def timestep_xmf(mesh_basename, data_basename, cycle, time_s, var_names,
                 n_cells, n_nodes, n_topo, mesh_cycle_key):
    """Return XML string for one per-timestep xmf file."""
    lines = [
        '<Xdmf Version="2.0" xmlns:xi="http://www.w3.org/2001/XInclude">',
        '  <Domain>',
        '    <Grid Name="Mesh">',
        f'      <Topology Name="mixedtopo" NumberOfElements="{n_cells}" TopologyType="Mixed">',
        f'        <DataItem DataType="Int" Dimensions="{n_topo}" Format="HDF">',
        f'          {mesh_basename}:/{mesh_cycle_key}/Mesh/MixedElements',
        f'        </DataItem>',
        f'      </Topology>',
        f'      <Geometry Name="geo" Type="XYZ">',
        f'        <DataItem DataType="Float" Dimensions="{n_nodes}  3" Format="HDF">',
        f'          {mesh_basename}:/{mesh_cycle_key}/Mesh/Nodes',
        f'        </DataItem>',
        f'      </Geometry>',
        f'      <Time Value="{time_s:.17e}"/>',
    ]
    for vname in var_names:
        lines += [
            f'      <Attribute Center="Cell" Name="{vname}" Type="Scalar">',
            f'        <DataItem DataType="Float" Dimensions="{n_cells}" Format="HDF">',
            f'          {data_basename}_data.h5:{vname}/{cycle}',
            f'        </DataItem>',
            f'      </Attribute>',
        ]
    lines += [
        '    </Grid>',
        '  </Domain>',
        '</Xdmf>',
    ]
    return '\n'.join(lines) + '\n'


def visit_xmf(data_basename, cycles):
    """Return top-level VisIt.xmf content referencing all per-timestep xmf files."""
    lines = [
        '<?xml version="1.0" ?>',
        '<!DOCTYPE Xdmf SYSTEM "Xdmf.dtd" []>',
        '<Xdmf Version="2.0" xmlns:xi="http://www.w3.org/2001/XInclude">',
        '  <Domain>',
        '    <Grid CollectionType="Temporal" GridType="Collection">',
    ]
    for cycle in cycles:
        lines.append(
            f'      <xi:include href="{data_basename}_data.h5.{cycle}.xmf"'
            f' xpointer="xpointer(//Xdmf/Domain/Grid)"/>'
        )
    lines += [
        '    </Grid>',
        '  </Domain>',
        '</Xdmf>',
        '',
    ]
    return '\n'.join(lines)


def process_level(hlevel, nc_files, run_dir, mesh_basename, out_basename,
                  var_filter, mesh_info):
    mesh_cycle_key, n_cells, n_nodes, n_topo = mesh_info

    all_surf_vars = surface_scalar_vars(nc_files[0])
    if var_filter is not None:
        missing = [v for v in var_filter if v not in all_surf_vars]
        if missing:
            print(f'  WARNING: variables not found in h{hlevel} files: {missing}')
        var_names = [v for v in var_filter if v in all_surf_vars]
    else:
        var_names = all_surf_vars

    if not var_names:
        print(f'  No variables to write for h{hlevel}, skipping.')
        return

    data_h5_path = os.path.join(run_dir, f'{out_basename}_data.h5')
    visit_xmf_path = os.path.join(run_dir, f'{out_basename}_data.VisIt.xmf')

    cycles = []
    cycle = 0

    with h5py.File(data_h5_path, 'w') as h5out:
        for nc_path in nc_files:
            ds = netCDF4.Dataset(nc_path)
            n_lndgrid = ds.dimensions['lndgrid'].size

            if n_cells is not None and n_lndgrid != n_cells:
                print(f'  ERROR: lndgrid={n_lndgrid} in {os.path.basename(nc_path)} '
                      f'does not match mesh n_cells={n_cells}. Skipping file.')
                ds.close()
                continue

            t_var = ds.variables['time']
            n_times = t_var.shape[0]

            for tidx in range(n_times):
                time_s = elm_time_to_seconds(t_var, tidx)

                for vname in var_names:
                    raw = ds.variables[vname][tidx, :]
                    data = raw.filled(np.nan) if hasattr(raw, 'filled') else np.asarray(raw)
                    grp = h5out.require_group(vname)
                    grp.create_dataset(str(cycle), data=data.astype(np.float64))

                xmf_str = timestep_xmf(
                    mesh_basename, out_basename, cycle, time_s, var_names,
                    n_lndgrid, n_nodes, n_topo, mesh_cycle_key)
                xmf_path = os.path.join(run_dir, f'{out_basename}_data.h5.{cycle}.xmf')
                with open(xmf_path, 'w') as xf:
                    xf.write(xmf_str)

                cycles.append(cycle)
                cycle += 1

            ds.close()

    with open(visit_xmf_path, 'w') as vf:
        vf.write(visit_xmf(out_basename, cycles))

    print(f'  Wrote {len(cycles)} timesteps to {data_h5_path}')
    print(f'  VisIt index: {visit_xmf_path}')


def main():
    args = parse_args()

    run_dir = os.path.abspath(args.run)
    if not os.path.isdir(run_dir):
        sys.exit(f'ERROR: run directory not found: {run_dir}')

    mesh_basename = f'ats_vis_{args.domain}_mesh.h5'
    mesh_path = os.path.join(run_dir, mesh_basename)
    if not os.path.isfile(mesh_path):
        sys.exit(f'ERROR: mesh file not found: {mesh_path}')

    out_basename = f'elm_vis_{args.domain}'
    var_filter = [v.strip() for v in args.vars.split(',')] if args.vars else None

    mesh_info = get_mesh_info(mesh_path)

    files_by_level = find_elm_files(run_dir, args.hlevel)
    if not files_by_level:
        sys.exit(f'ERROR: no ELM history files found in {run_dir}')

    for hlevel, nc_files in sorted(files_by_level.items()):
        suffix = f'_h{hlevel}' if len(files_by_level) > 1 else ''
        level_basename = out_basename + suffix
        print(f'Processing h{hlevel}: {len(nc_files)} file(s) -> {level_basename}')
        process_level(hlevel, nc_files, run_dir, mesh_basename, level_basename,
                      var_filter, mesh_info)


if __name__ == '__main__':
    main()
