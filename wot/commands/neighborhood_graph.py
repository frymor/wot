#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import scanpy.api as sc
import wot.io


def main(argv):
    parser = argparse.ArgumentParser(description='Compute neighborhood graph')
    parser.add_argument('--matrix', help=wot.commands.MATRIX_HELP, required=True)
    parser.add_argument('--gene_filter',
                        help='File with one gene id per line to include from the matrix')
    parser.add_argument('--cell_filter',
                        help='File with one cell id per line to include from the matrix')
    parser.add_argument('--transpose', help='Transpose the matrix', action='store_true')
    parser.add_argument('--pca_comps',
                        help='Number of PCA components.',
                        type=int, default=50)
    parser.add_argument('--diff_comps',
                        help='Number of diffusion components.',
                        type=int, default=15)
    parser.add_argument('--neighbors', help='Number of nearest neighbors',
                        type=int, default=15)
    parser.add_argument('--space', help='Space to compute the neighborhood graph in', choices=['dmap', 'pca', 'input'])
    parser.add_argument('--out',
                        help='Output file name. The file is saved in gexf format (https://gephi.org/gexf/format/)')

    args = parser.parse_args(argv)
    if args.out is None:
        args.out = 'wot-neighborhood-graph'
    space = args.space
    neighbors = args.neighbors
    pca_comps = args.pca_comps
    diff_comps = args.diff_comps
    adata = wot.io.read_dataset(args.matrix)
    if args.transpose:
        adata = adata.T
    if args.cell_filter is not None:
        adata = adata[adata.obs.index.isin(wot.io.read_sets(args.cell_filter).obs.index)].copy()
    if args.gene_filter is not None:
        adata = adata[:, adata.var.index.isin(wot.io.read_sets(args.gene_filter).obs.index)].copy()

    if space == 'pca':
        sc.tl.pca(adata, n_comps=pca_comps)
        sc.pp.neighbors(adata, use_rep='X_pca', n_neighbors=neighbors)
    elif space == 'dmap':
        sc.tl.pca(adata, n_comps=pca_comps)
        sc.pp.neighbors(adata, use_rep='X_pca', n_neighbors=neighbors)
        sc.tl.diffmap(adata, n_comps=diff_comps)
        sc.pp.neighbors(adata, use_rep='X_diffmap', n_neighbors=neighbors)
    else:
        sc.pp.neighbors(adata, use_rep='X', n_neighbors=neighbors)

    W = adata.uns['neighbors']['connectivities']
    n_obs = W.shape[0]
    obs_ids = adata.obs.index.values
    with open(args.out + '.gexf', 'w') as writer:
        writer.write('<?xml version="1.0" encoding="UTF-8"?>')
        writer.write(
            '<gexf xmlns="http://www.gexf.net/1.2draft" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd" version="1.2">')
        writer.write('<graph defaultedgetype="undirected">')
        writer.write('<nodes>')

        for j in range(n_obs):
            writer.write('<node id="{id}" label="{id}" />'.format(id=obs_ids[j]))
        writer.write('</nodes>')
        writer.write('<edges>')
        rows, cols = W.nonzero()
        edge_counter = 1
        for i, j in zip(rows, cols):
            if i < j:
                writer.write(
                    '"<edge id="{id}" source="{s}" target="{t}" weight="{w}" />'.format(id=edge_counter, s=obs_ids[i],
                                                                                        t=obs_ids[j], w=W[i, j]))
                edge_counter = edge_counter + 1
        writer.write('</edges>')
        writer.write('</graph>')
        writer.write('</gexf>')
    # <?xml version="1.0" encoding="UTF-8"?>
    # <gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
    #     <meta lastmodifieddate="2009-03-20">
    #         <creator>Gexf.net</creator>
    #         <description>A hello world! file</description>
    #     </meta>
    #     <graph mode="static" defaultedgetype="directed">
    #         <nodes>
    #             <node id="0" label="Hello" />
    #             <node id="1" label="Word" />
    #         </nodes>
    #         <edges>
    #             <edge id="0" source="0" target="1" />
    #         </edges>
    #     </graph>
    # </gexf>
