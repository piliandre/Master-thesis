import os
import rasterio
import numpy as np
import glob
import fiona
import rasterio.mask
import gdal
import matplotlib.pyplot as plt
import csv
import gc



########### Functions / Classes inicialization #############


class Cathegory_WM_Class:
    def __init__(self, id, name, lowerLimit, upperLimit):
        self.ID = id
        self.name = name
        self.lowerLimit = lowerLimit
        self.upperLimit = upperLimit
        self.data = []


        #self.numberOfPixels = []
        #self.km2 = []
        #self.mean = []

        #self.maxVal = []
        #self.minVal = []
        #self.std = []
        #self.var = []
        #self.resDic = []

    def calculate_Metrics(self):

        if len(self.data) == 0:
            data_array = 0
        else:
            data_array = self.data
        self.numberOfPixels = len(self.data)
        self.km2 = self.numberOfPixels * (1e-5)  # 1 pixel = 10m2 = 1e-5km2
        self.mean = np.nanmean(data_array)
        self.maxVal = np.nanmax(data_array)
        self.minVal = np.nanmin(data_array)
        self.std = np.nanstd(data_array)  # Standard deviation
        self.var = np.nanvar(data_array)  # Variance

        # box plot
        #fig1, ax1 = plt.subplots()
        #ax1.set_title(self.name)
        #self.resDic = ax1.boxplot(self.data)

    def store_Data(self, path_Out, test_Name, shp_Leyend, NDVI_band_number):
        #csv_file_name = path_Out + test_Name + '.csv'
        csv_file_name = path_Out +'result.csv'

        fieldnames = ["timestamp", "ID", "name", "lowerLimit", "upperLimit",
                      "shp_Leyend",
                      "NDVI_band_number",
                      "test_Name", "path_WM", "path_NDVI", "path_SHP", "path_Out",
                      "numberOfPixels", "km2", "mean",
                      "maxVal", "minVal", "std", "var"]

        # Calcula el timestamp
        from time import gmtime, strftime
        ts = strftime("%Y%m%d_%H%M%S", gmtime())

        path_SHP=[]
        for path_SHP_dict in path_SHP_dict_List:
            path_SHP.append(path_SHP_dict["path_SHP"])
        path_SHP = " ".join(path_SHP)

        data2write = [ts, self.ID, self.name, self.lowerLimit, self.upperLimit,
                      shp_Leyend,
                      NDVI_band_number,
                      test_Name, path_WM, path_NDVI, path_SHP, path_Out,
                      self.numberOfPixels, self.km2, self.mean, 
                      self.maxVal, self.minVal, self.std, self.var]

        # checks if csv file already exists
        my_file_exist = os.path.isfile(csv_file_name)

        # Writes data to CSV file
        with open(csv_file_name, mode='a') as csv_file:
            writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            if not my_file_exist:  # file doesn't exist
                writer.writerow(fieldnames)
            writer.writerow(data2write)


def select_Images(path_images, imgFootprint):
    filenameImages_List = []
    for filename in sorted(os.listdir(path_images)):
        if ('.aux.xml' not in filename) & ('.tif' in filename) & ('.tif.' not in filename):
            if imgFootprint in filename:
                print filename
                filenameImages_List.append(filename)
    return filenameImages_List


def selectCategoryMask(img_band, lowerLimit, upperLimit):
    res = []
    if upperLimit == 100:
        res = (img_band >= lowerLimit) & (img_band <= upperLimit)
    elif upperLimit == lowerLimit:  # NoData values
        res = (img_band == lowerLimit)
    else:
        res = (img_band >= lowerLimit) & (img_band < upperLimit)

    return res


def select_NDVI_array(band_NDVI, category_Mask):
    band_CategoryNDVI = band_NDVI[category_Mask]
    return img2Array(band_CategoryNDVI)


def img2Array(img_band):
    temp = np.array(img_band).ravel()  # Command optimized for speed
    # temp= np.asarray(img_band).ravel() # Command optimized for memory
    return temp


def select_ClassFromSHP(path_img, band2retrieve, geoms, geoms_InvalidData):
    with rasterio.open(path_img) as src:
        if len(geoms) == 0:
            out_image = src.read(band2retrieve)
        else:
            out_image, out_transform = rasterio.mask.mask(src, geoms, crop=False)

            """
            out_meta = src.meta.copy()
            out_meta.update({"driver": "GTiff",
                             "height": out_image.shape[1],
                             "width": out_image.shape[2],
                             "transform": out_transform})
            with rasterio.open(path_Out+"FirstScript.tif", "w", **out_meta) as dest:
                dest.write(out_image)
            """

        if len(geoms_InvalidData)>0:
            out_image_valid_data, out_transform = rasterio.mask.mask(src, geoms_InvalidData, crop=False, nodata=src.nodata, invert=True)
            invalid_data_mask = (out_image_valid_data == src.nodata)
            out_image[invalid_data_mask] = src.nodata

            """
            out_meta = src.meta.copy()
            out_meta.update({"driver": "GTiff",
                             "height": out_image.shape[1],
                             "width": out_image.shape[2],
                             "transform": out_transform})
            with rasterio.open(path_Out + "SecondScript.tif", "w", **out_meta) as dest:
                dest.write(out_image)
            """


        return out_image

def select_GeomsFromSHP(path_SHP_dict_List, shp_Leyend, footprint):
    geoms_list = []
    geoms_InvalidData_list = []
    for path_SHP_dict in path_SHP_dict_List:
        if path_SHP_dict["projection_ID"] in footprint:
            with fiona.open(path_SHP_dict["path_SHP"], "r") as shapefile:  # *** # write shp only, if you give a direct path in the line before
                if path_SHP_dict["filter_shp_by_Leyend"] == True:
                    for feature in shapefile:
                        leyenda = feature["properties"]["LEYENDA"]
                        leyenda = leyenda.encode('ascii', 'ignore').decode('ascii')
                        if (leyenda in shp_Leyend):
                            geoms = feature["geometry"]
                            geoms_list.append(geoms)
                else:
                    geoms_list = [feature["geometry"] for feature in shapefile]

            if len(path_SHP_dict["path_SHP_InvalidData"])>0:
                with fiona.open(path_SHP_dict["path_SHP_InvalidData"],"r") as shapefile:  # *** # write shp only, if you give a direct path in the line before
                    geoms_InvalidData_list = [feature["geometry"] for feature in shapefile]
    return geoms_list , geoms_InvalidData_list



########## Global variables inicialization ###########

path_WM = "E:/Orinoco/WM_merged/2_WaterDetectedYear/percentage/"#"F:/DiegoTest/InputWM/"
path_NDVI = "E:/Orinoco/w_inputNDVI/2017winter/"#"F:/DiegoTest/InputNDVI/Tiff_Imgs/"
NDVI_band_name = "NDVImean"
path_Out = "F:/DiegoTest/OutCSV/"
test_Name = "WMyear_NDVI2017winter"#"testAndDebug"
imgFootprint_List = ["18NYK", "18NYL", "18NYM", "18NZL", "18NZM", "19NBF", "19NBG", "19NCG"] #"18NZK",
#imgFootprint_List = ["19NBG", "19NCG"]

category_WM_List = []
category_WM_List.append(Cathegory_WM_Class(0, "NoWater", 0, 1))
category_WM_List.append(Cathegory_WM_Class(1, "ShortTerm", 1, 10))
category_WM_List.append(Cathegory_WM_Class(2, "MediumTerm", 10, 40))
category_WM_List.append(Cathegory_WM_Class(3, "LongTerm", 40, 95))
category_WM_List.append(Cathegory_WM_Class(4, "Always", 95, 100))
category_WM_List.append(Cathegory_WM_Class(5, "AllClassData", 0, 100))

path_SHP_dict_List = []
path_SHP_dict_List.append(dict(projection_ID="18N",
                               filter_shp_by_Leyend=True,
                               path_SHP="F:/DiegoTest/InputSHP/Casanare_Classes/Corine.shp",
                               path_SHP_InvalidData="E:/Orinoco/DEM/mask3/InvalidData.shp"))
path_SHP_dict_List.append(dict(projection_ID="19N",
                               filter_shp_by_Leyend=True,
                               path_SHP="F:/DiegoTest/InputSHP/Casanare_Classes/Corine19.shp",
                               path_SHP_InvalidData=[]))

shp_Leyend_List = [
#            "1.1.2. Tejido urbano discontinuo",
    "3.2.1.2.1. Herbazal abierto arenoso",
    "2.4.5. Mosaico de cultivos con espacios naturales",
    "3.1.1.2.1. Bosque denso bajo de tierra firme",
    "3.1.2.1.2. Bosque abierto alto inundable",
    "3.2.2.1. Arbustal denso",
    "3.1.2.2.1. Bosque abierto bajo de tierra firme",
    "2.1.2.1. Arroz",
    "3.1.3.1. Bosque fragmentado con pastos y cultivos",
#          "1.4.2. Instalaciones recreativas",
    "3.1.2.2.2. Bosque abierto bajo inundable",
    "3.1.3.2. Bosque fragmentado con vegetacin secundaria",
    "5.1.4. Cuerpos de agua artificiales",
    "3.3.3. Tierras desnudas y degradadas",
    "3.1.2.1.1. Bosque abierto alto de tierra firme",
    "2.3.3. Pastos enmalezados",
    "2.2.3.2. Palma de aceite",
#          "1.1.1. Tejido urbano continuo",
    "3.2.1.1.2.1. Herbazal denso inundable no arbolado",
#         "1.2.4. Aeropuertos",
    "2.3.1. Pastos limpios",
    "4.1.3. Vegetacin acutica sobre cuerpos de agua",
    "3.2.3. Vegetacin secundaria o en transicin",
    "3.1.3. Bosque fragmentado",
    "3.1.1.1.1. Bosque denso alto de tierra firme",
#         "5.1.1. Ros (50 m)",
    "3.1.1.1.2. Bosque denso alto inundable",
    "5.1.2. Lagunas, lagos y cinagas naturales",
    "2.1.1. Otros cultivos transitorios",
    "3.3.1. Zonas arenosas naturales",
    "2.4.2. Mosaico de pastos y cultivos",
    "1.3.1.2. Explotacin de hidrocarburos",
    "3.1.1.2.2. Bosque denso bajo inundable",
    "2.2.3.1. Otros cultivos permanentes arbreos",
    "3.1.4. Bosque de galera y ripario",
    "3.2.2.2. Arbustal abierto",
    "4.1.1. Zonas Pantanosas",
    "3.2.1.1.2. Herbazal denso inundable",
    "2.3.2. Pastos arbolados",
    "2.4.4. Mosaico de pastos con espacios naturales",
    "3.1.5. Plantacin forestal",
    "2.4.3. Mosaico de cultivos, pastos y espacios naturales",
    "3.2.1.1.1. Herbazal denso de tierra firme",
    "3.3.4. Zonas quemadas"
    ]

######### Main code ##########


for shp_Leyend in shp_Leyend_List:
    for i in range(len(category_WM_List)):
        for imgFootprint in imgFootprint_List:
            print " footprint " + imgFootprint
            print "Calculating geoms for the LEYEND: " + shp_Leyend
            shp_geoms_list, shp_geoms_InvalidData_list = select_GeomsFromSHP(path_SHP_dict_List, shp_Leyend, imgFootprint)


            # Lists the WM and NDVI by footprint (there should only be one)
            filename_WM = select_Images(path_WM, imgFootprint)
            filename_NDVI = select_Images(path_NDVI, imgFootprint)

            # Validations (there should be only one
            assert (len(filename_WM) > 0), "ERROR: NO existe un WM para el Footprint"
            assert (len(filename_WM) < 2), "ERROR: Existe mas de un WM para un Footprint"
            assert (len(filename_NDVI) > 0), "ERROR: NO existe un NDVI para el Footprint"
            assert (len(filename_NDVI) < 2), "ERROR: No hay imagines NDVI disponibles para ese footprint"

            # Opens WM and NDVI from the classes
            print "loading WM and NDVI images"
            band_WM_SHP = select_ClassFromSHP(path_WM + filename_WM[0], 1, shp_geoms_list,shp_geoms_InvalidData_list)
            band_NDVI = select_ClassFromSHP(path_NDVI + filename_NDVI[0], 1, shp_geoms_list,shp_geoms_InvalidData_list)

            #from osgeo import gdal
            #ds = gdal.Open(path_NDVI + filename_NDVI[0])
            #channel = np.array(ds.GetRasterBand(1).ReadAsArray())
            if "S2Stats_19NBG_ndvi_Mean.Band_1.tif" in filename_NDVI[0]:
                print "ops"

            # Validate Data

            nan_Mask = np.isnan(band_WM_SHP) | np.isnan(band_NDVI) | (band_NDVI == -9999)
            if nan_Mask.all(): # Todos son nan
                print "WARNING: Todos los  pixeles son NaN"
            elif nan_Mask.any():  # Existe un nan
                print "WARNING: existen pixeles nan"
            band_WM_SHP[nan_Mask] = 255
            band_NDVI[nan_Mask] = 255

            # Creates a mask for a given given category
            band_WM_SHP_CategoryMask = selectCategoryMask(band_WM_SHP, category_WM_List[i].lowerLimit,
                                                          category_WM_List[i].upperLimit)
            # Retrieves all the NDVI data within a given category
            band_WM_SHP_Category_NDVI_array = select_NDVI_array(band_NDVI, band_WM_SHP_CategoryMask)

            # Temporary stores the information for a the selected footprint
            category_WM_List[i].data.extend(band_WM_SHP_Category_NDVI_array)


        print "Calculating metrics for the given shapefile class"
        category_WM_List[i].calculate_Metrics()

        category_WM_List[i].store_Data(path_Out, test_Name, shp_Leyend, NDVI_band_name)

        # resets the stored data before trying with a different classID shapefile for the next looop
        category_WM_List[i].data = []

        gc.collect()


print 'Done!!!'