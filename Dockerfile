FROM jupyter/datascience-notebook

RUN conda install -y shapely qgrid folium geojson gdal appmode
RUN pip install hublib

RUN git clone https://github.com/hydroglobe-ec/ecube2021.git
RUN mv ./ecube2021/* .
RUN rm -rf work ecube2021