"""Transform an Excel file to a KML file

Group the placemarks by folders, color & shapes based on values in the table

"""


# pylint: disable=invalid-name


from typing import Any, List

import pandas as pd
from lxml import etree
from pykml.factory import KML_ElementMaker as KML

from table2kml import styling
from table2kml.helper import load_icon_shapes


__author__ = "Daniel K. Komesu"
__author_email__ = "danielkomesu@gmail.com"
__version__ = "0.1.0"


class Options:
    """An object to store options passed to the functions in this module

    Required parameters
    -------------------
    lat, lon : float
        The column names of a Pandas DataFrame coordinates (latitude, longitude)
    """
    def __init__(self, lat, lon, **kwargs):
        self.ICON_SHAPES = load_icon_shapes()
        self.style = styling.StyleOptions()
        self.lat = lat
        self.lon = lon
        # List of column names that will be added in point's description
        self.data_cols = []
        # Point names by value in column `name_col`
        self.name = None
        # Separate points in folders by values in column `folder_col`
        self.folders = []
        # Color points by value in column `color_col`
        self.color = None
        # Altitude of points (relative to ground) by value in column `height_col`
        self.altitude = None
        self.shape = self.ICON_SHAPES["donut"]
        for key in kwargs:
            if key == "style":
                for style_key in kwargs[key]:
                    self.style.__setattr__(style_key, kwargs[key][style_key])
            else:
                self.__setattr__(key, kwargs[key])


def make_description(row: pd.core.series.Series, data_cols) -> KML.description:
    """Create a description KML object with the data in row[data_cols]

    Parameters
    ----------
    row : pd.core.series.Series
        A row of dataframe with the information to use in the description text
    data_cols : list
        A list of columns in the row

    Returns
    -------
    KML.description
        The KML description object
    """
    description = KML.description(
        "\n".join([f"{col}: {row[col]}" for col in data_cols])
    )
    return description


def make_placemark(row: pd.core.series.Series, opt: Options) -> KML.Placemark:
    """Create a placemark KML object with data in `row` and configuration in opt

    Parameters
    ----------
    row : pd.core.series.Series, dict, namedtuple
        An iterable with values accessible by a key
    opt : Options
        The options to use as parameters

    Returns
    -------
    KML.Placemark
        A KML placemark object
    """
    lat, lon = row[opt.lat], row[opt.lon]
    placemark = KML.Placemark()
    if opt.name:
        placemark.append(KML.name(row[opt.name]))
    # Point
    altitude = row[opt.altitude] if opt.altitude is not None else 0
    point = KML.Point(KML.coordinates(f"{lon},{lat},{altitude}"))
    alt_mode = KML.altitudeMode("relativeToGround")
    point.append(alt_mode)
    placemark.append(point)
    # Style
    if opt.style.icon_color is not None:
        style_url = "#color_" + str(row["ColorDigit"])
        placemark.append(KML.styleUrl(style_url))
    description = make_description(row, opt.data_cols)
    placemark.append(description)
    return placemark


def make_folder(
        data: pd.core.frame.DataFrame,
        name: str, opt: Options
    ) -> KML.Folder:
    """Create a folder with the data provided

    Parameters
    ----------
    data : pd.core.frame.DataFrame
        The data used to create the placemarks
    name : str
        The name of the folder created
    opt : Options
        Options to create the placemarks

    Returns
    -------
    KML.Folder
        Resulting KML folder with placemarks
    """
    folder = KML.Folder(KML.name(name))
    for i in range(data.shape[0]):
        row = data.iloc[i]
        placemark = make_placemark(row, opt)
        folder.append(placemark)
    return folder


def make_tree(
        parent: Any,
        data: pd.core.frame.DataFrame,
        folders: List[str],
        opt: Options
    ) -> Any:
    """Create a tree of folders

    Parameters
    ----------
    parent : KML object
        The parent object to append to
    data : pd.core.frame.DataFrame
        The data with the columns to be used to build the tree
    folders : list
        List of columns names in data
    opt : Options
        The options for this function

    Returns
    -------
    parent
        The parent object with the tree appended to it
    """
    # pylint: disable=invalid-name
    for l0 in data[folders[0]].unique():
        data0 = data[data[folders[0]] == l0]
        if len(folders) > 1:
            f0 = KML.Folder(KML.name(folders[0] + ": " + str(l0)))
            f0 = make_tree(
                parent=f0,
                data=data0,
                folders=folders[1:],
                opt=opt,
            )
        else:
            f0 = make_folder(
                data=data0,
                name=folders[0] + ": " + str(l0),
                opt=opt,
            )
        parent.append(f0)
    return parent


def make_kml(
        data: pd.core.frame.DataFrame,
        opt: Options,
        doc_name: str = "Default"
    ) -> KML.kml:
    """Create a KML object with data and opt configuration

    Parameters
    ----------
    data : pd.core.frame.DataFrame
        A Pandas DataFrame with the data to use as input
    opt : Options
        An Options instance with the configuration to output the KML
    doc_name : str, optional
        The document name of KML object, by default "Default"

    Returns
    -------
    pykml.KML
        The resulting KML object
    """
    kml = KML.kml()
    doc = KML.Document(KML.name(doc_name))
    kml.append(doc)

    if opt.style is not None:
        data = styling.add_color_digit_column(
            df=data,
            column_name=opt.style.icon_color,
            n_colors=opt.style.icon_n_colors,
        )
        styles = styling.make_styles(
            data=data,
            opts=opt.style,
        )
        for style in styles:
            doc.append(style)

    if opt.folders is not None:
        doc = make_tree(
            parent=doc,
            data=data,
            folders=opt.folders,
            opt=opt,
        )
        return kml

    for i in range(data.shape[0]):
        row = data.iloc[i]
        placemark = make_placemark(row, opt)
        doc.append(placemark)
    return kml


def save_kml(kml: KML.kml, filepath: str):
    """Save a KML object to a file

    Parameters
    ----------
    kml : KML.kml
        The object to save
    filepath : str
        Path to save the file
    """
    # pylint: disable=c-extension-no-member
    with open(filepath, "wb") as f:
        f.write(etree.tostring(kml, pretty_print=True))
