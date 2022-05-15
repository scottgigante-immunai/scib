import pandas as pd
from sklearn.metrics.cluster import silhouette_samples, silhouette_score


def silhouette(adata, label_key, embed, metric="euclidean", scale=True):
    """Average silhouette width (ASW)

    Wrapper for sklearn silhouette function values range from [-1, 1] with

        * 1 indicates distinct, compact clusters
        * 0 indicates overlapping clusters
        * -1 indicates core-periphery (non-cluster) structure

    By default, the score is scaled between 0 and 1 (``scale=True``).
    The function requires an embedding to be stored in ``adata.obsm`` and can only be applied to feature and embedding
    integration outputs.
    See below for examples of preprocessing and function calls.

    :param label_key: key in adata.obs of cell labels
    :param embed: embedding key in adata.obsm, default: 'X_pca'
    :param scale: default True, scale between 0 (worst) and 1 (best)

    **Preprocessing: Feature output**

    Feature output requires processing of the count matrix in the following steps:

        1. Highly variable gene selection (skip, if working on feature space subset)
        2. PCA

    .. code-block:: python

        scib.pp.reduce_data(adata, n_top_genes=2000, pca=True)
        scib.me.isolated_labels_asw(adata, label_key="celltype", embed="X_pca")

    **Preprocessing Embedding output**

    No preprocessing is required.
    The embedding should be stored in ``adata.obsm``, by default under key ``'X_embed'``.

    .. code-block:: python

        scib.me.silhouette(adata, label_key="celltype", embed="X_emb")
    """
    if embed not in adata.obsm.keys():
        print(adata.obsm.keys())
        raise KeyError(f"{embed} not in obsm")
    asw = silhouette_score(
        X=adata.obsm[embed], labels=adata.obs[label_key], metric=metric
    )
    if scale:
        asw = (asw + 1) / 2
    return asw


def silhouette_batch(
    adata,
    batch_key,
    label_key,
    embed,
    metric="euclidean",
    return_all=False,
    scale=True,
    verbose=True,
):
    """Batch ASW

    Modified average silhouette width (ASW) of batch

    This metric measures the silhouette of a given batch.
    It assumes that a silhouette width close to 0 represents perfect overlap of the batches, thus the absolute value of
    the silhouette width is used to measure how well batches are mixed.
    For all cells :math:`i` of a cell type :math:`C_j`, the batch ASW of that cell type is:

    .. math::

        batch \\, ASW_j = \\frac{1}{|C_j|} \\sum_{i \\in C_j} |silhouette(i)|

    The final score is the average of the absolute silhouette widths computed per cell type :math:`M`.

    .. math::

        batch \\, ASW = \\frac{1}{|M|} \\sum_{i \\in M} batch \\, ASW_j

    For a scaled metric (which is the default), the absolute ASW per group is subtracted from 1 before averaging, so that
    0 indicates suboptimal label representation and 1 indicates optimal label representation.

    .. math::

        batch \\, ASW_j = \\frac{1}{|C_j|} \\sum_{i \\in C_j} 1 - |silhouette(i)|

    The function requires an embedding to be stored in ``adata.obsm`` and can only be applied to feature and embedding
    integration outputs.
    See below for examples of preprocessing and function calls.

    :param batch_key: batch labels to be compared against
    :param label_key: group labels to be subset by e.g. cell type
    :param embed: name of column in adata.obsm
    :param metric: see sklearn silhouette score
    :param scale: if True, scale between 0 and 1
    :param return_all: if True, return all silhouette scores and label means
        default False: return average width silhouette (ASW)
    :param verbose: print silhouette score per group
    :return:
        Batch ASW  (always)
        Mean silhouette per group in pd.DataFrame (additionally, if return_all=True)
        Absolute silhouette scores per group label (additionally, if return_all=True)

    **Preprocessing: Feature output**

    Feature output requires processing of the count matrix in the following steps:

        1. Highly variable gene selection (skip, if working on feature space subset)
        2. PCA

    .. code-block:: python

        scib.pp.reduce_data(adata, n_top_genes=2000, pca=True)
        scib.me.silhouette_batch(adata, batch_key="batch", label_key="celltype", embed="X_pca")

    **Preprocessing Embedding output**

    No preprocessing is required.
    The embedding should be stored in ``adata.obsm``, by default under key ``'X_embed'``.

    .. code-block:: python

        scib.me.silhouette_batch(adata, batch_key="batch", label_key="celltype", embed="X_emb")

    """
    if embed not in adata.obsm.keys():
        print(adata.obsm.keys())
        raise KeyError(f"{embed} not in obsm")

    sil_all = pd.DataFrame(columns=["group", "silhouette_score"])

    for group in adata.obs[label_key].unique():
        adata_group = adata[adata.obs[label_key] == group]
        n_batches = adata_group.obs[batch_key].nunique()

        if (n_batches == 1) or (n_batches == adata_group.shape[0]):
            continue

        sil_per_group = silhouette_samples(
            adata_group.obsm[embed], adata_group.obs[batch_key], metric=metric
        )

        # take only absolute value
        sil_per_group = [abs(i) for i in sil_per_group]

        if scale:
            # scale s.t. highest number is optimal
            sil_per_group = [1 - i for i in sil_per_group]

        sil_all = sil_all.append(
            pd.DataFrame(
                {
                    "group": [group] * len(sil_per_group),
                    "silhouette_score": sil_per_group,
                }
            )
        )

    sil_all = sil_all.reset_index(drop=True)
    sil_means = sil_all.groupby("group").mean()
    asw = sil_means["silhouette_score"].mean()

    if verbose:
        print(f"mean silhouette per group: {sil_means}")

    if return_all:
        return asw, sil_means, sil_all

    return asw
