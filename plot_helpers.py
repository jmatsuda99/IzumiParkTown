import matplotlib.pyplot as plt


def create_line_plot(
    x,
    y,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    figsize=(10, 5),
    rotation: int = 0,
    marker: str | None = None,
    markersize: int | None = None,
    label: str | None = None,
):
    fig, ax = plt.subplots(figsize=figsize)
    plot_kwargs = {}
    if marker is not None:
        plot_kwargs["marker"] = marker
    if markersize is not None:
        plot_kwargs["markersize"] = markersize
    if label is not None:
        plot_kwargs["label"] = label

    ax.plot(x, y, **plot_kwargs)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if rotation:
        ax.tick_params(axis="x", rotation=rotation)
    ax.grid(True)
    if label is not None:
        ax.legend()
    fig.tight_layout()
    return fig, ax


def create_multi_line_plot(
    series,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    figsize=(11, 5),
    rotation: int = 0,
    marker: str | None = None,
    markersize: int | None = None,
):
    fig, ax = plt.subplots(figsize=figsize)
    for item in series:
        plot_kwargs = {"label": item["label"]}
        if marker is not None:
            plot_kwargs["marker"] = marker
        if markersize is not None:
            plot_kwargs["markersize"] = markersize
        ax.plot(item["x"], item["y"], **plot_kwargs)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if rotation:
        ax.tick_params(axis="x", rotation=rotation)
    ax.grid(True)
    if series:
        ax.legend()
    fig.tight_layout()
    return fig, ax


def create_bar_plot(
    x,
    y,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    figsize=(10, 5),
    rotation: int = 0,
):
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x, y)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if rotation:
        ax.tick_params(axis="x", rotation=rotation)
    fig.tight_layout()
    return fig, ax


def create_grouped_bar_plot(
    categories,
    series,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    figsize=(12, 5),
    rotation: int = 0,
    width: float = 0.38,
):
    fig, ax = plt.subplots(figsize=figsize)
    x_positions = list(range(len(categories)))
    if len(series) != 2:
        raise ValueError("create_grouped_bar_plot currently expects exactly 2 series.")

    ax.bar([i - width / 2 for i in x_positions], series[0]["values"], width=width, label=series[0]["label"])
    ax.bar([i + width / 2 for i in x_positions], series[1]["values"], width=width, label=series[1]["label"])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(categories, rotation=rotation)
    ax.legend()
    fig.tight_layout()
    return fig, ax


def create_heatmap_plot(
    values,
    yticklabels,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
    colorbar_label: str,
    figsize=(14, 6),
):
    fig, ax = plt.subplots(figsize=figsize)
    image = ax.imshow(values, aspect="auto", interpolation="nearest")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_yticks(range(len(yticklabels)))
    ax.set_yticklabels(yticklabels)
    fig.colorbar(image, ax=ax, label=colorbar_label)
    fig.tight_layout()
    return fig, ax
