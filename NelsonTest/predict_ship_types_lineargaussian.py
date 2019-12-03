import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from datetime import timedelta
from bayou.datastructures import Gaussian, GaussianSequence
from bayou.filters.lineargaussian import Kalman
from bayou.utils import Utility

"""The scripts is used to predict ship types.
This script reads a testing AIS file. MMSI, Latitudes, Longitudes, Time are necessary.
It processes and filter the data as in "read_ais_and_train_lineargaussian".
It generates the exact same structure of data as in "read_ais_and_train_lineargaussian".
Then, it tests all the (sub-)tracks and gives out a probability being each type.
"""

# We have the dynamic models for the following types
ShipTypes = ["Cargo", "Passenger", "Tanker", "Tug", "Vessel-Fishing"]

# Read and process data
# This testing file is generated by merging all the files in "processed-AIS/"
input_path = "processed-ais-for-predict/"
data_ais = pd.read_csv(input_path + "ais-data-for-testing.csv")
ais_groupby_mmsi = pd.DataFrame.groupby(data_ais, "MMSI")

# Data processing. It is the same with "read_ais_and_train_lineargaussian"
seperated_tracks = []
for this_boat in ais_groupby_mmsi:
    this_mmsi = this_boat[0]
    this_time = list(this_boat[1]["Time"])
    this_lat = list(this_boat[1]["Latitude"])
    this_lon = list(this_boat[1]["Longitude"])
    this_continuous_track_idx = []
    prev_time = []
    prev_lat = []
    prev_lon = []
    for i, this_row_time in enumerate(this_time):
        proc_time = datetime.strptime(this_row_time, "%Y-%m-%dT%H:%M:%SZ")
        if prev_time == []:
            prev_time = proc_time
            prev_lat = this_lat[i]
            prev_lon = this_lon[i]
            this_continuous_track_idx.append(i)
        else:
            if (this_lat[i] < 90) & (this_lat[i] > -90):
                if ((proc_time - prev_time) < timedelta(hours=1.5)) & (np.abs(prev_lat-this_lat[i]) <= 1.0) &\
                        (np.abs(prev_lon-this_lon[i]) <= 1.0):
                    this_continuous_track_idx.append(i)
                else:
                    if len(this_continuous_track_idx) >= 80:
                        this_continuous_track = {}
                        this_continuous_track["mmsi"] = this_mmsi
                        this_continuous_track["lat"] = [this_lat[k] for k in this_continuous_track_idx]
                        this_continuous_track["lon"] = [this_lon[k] for k in this_continuous_track_idx]
                        seperated_tracks.append(this_continuous_track)
                        this_continuous_track_idx = []
                    else:
                        this_continuous_track_idx = [i]
                prev_time = proc_time
                prev_lat = this_lat[i]
                prev_lon = this_lon[i]
            else:
                if len(this_continuous_track_idx) >= 80:
                    this_continuous_track = {}
                    this_continuous_track["mmsi"] = this_mmsi
                    this_continuous_track["lat"] = [this_lat[k] for k in this_continuous_track_idx]
                    this_continuous_track["lon"] = [this_lon[k] for k in this_continuous_track_idx]
                    seperated_tracks.append(this_continuous_track)
                    this_continuous_track_idx = []
                else:
                    this_continuous_track_idx = []
                prev_time = []
                prev_lat = []
                prev_lon = []

    if len(this_continuous_track_idx) >= 80:
        this_continuous_track = {}
        this_continuous_track["mmsi"] = this_mmsi
        this_continuous_track["lat"] = [this_lat[k] for k in this_continuous_track_idx]
        this_continuous_track["lon"] = [this_lon[k] for k in this_continuous_track_idx]
        seperated_tracks.append(this_continuous_track)
        this_continuous_track_idx = []

print("Reading data finished ...")

# Create latitude and longitude data
dataset_lat = []
dataset_lon = []
for i, this_track in enumerate(seperated_tracks):
    # The latitudes are scaled to 100 times. It avoids some numeric issues.
    this_track_array_lat = np.asarray(this_track["lat"]) * 100
    # It takes the first measurement as the initial state
    initial_state = Gaussian(np.array([[this_track_array_lat[0]], [0]]), np.eye(2))
    # Construct sequence for prediction.
    sequence = GaussianSequence(np.expand_dims(this_track_array_lat, axis=-1), initial_state)
    dataset_lat.append(sequence)
    # The longitudes are scaled to 100 times as well.
    this_track_array_lon = np.asarray(this_track["lon"]) * 100
    # It takes the first measurement as the initial state
    initial_state = Gaussian(np.array([[this_track_array_lon[0]], [0]]), np.eye(2))
    sequence = GaussianSequence(np.expand_dims(this_track_array_lon, axis=-1), initial_state)
    dataset_lon.append(sequence)

# load models
models = []
for i, this_shiptype in enumerate(ShipTypes):
    fid = open("models/"+this_shiptype+".data", "rb")
    models.append(pickle.load(fid))
    fid.close()

# predict
predictions = []
for i in range(len(dataset_lat)):
    # Latitude prediction
    this_data_lat = dataset_lat[i]
    likelihood_lat_for_type = []
    for j, this_shiptype in enumerate(ShipTypes):
        sequence_lat = Kalman.filter_sequence(this_data_lat, models[j]["Latitude"])
        likelihood_lat_for_type.append(np.sum(sequence_lat.loglikelihood))
    # Longitude prediction
    this_data_lon = dataset_lon[i]
    likelihood_lon_for_type = []
    for j, this_shiptype in enumerate(ShipTypes):
        sequence_lon = Kalman.filter_sequence(this_data_lon, models[j]["Longitude"])
        likelihood_lon_for_type.append(np.sum(sequence_lon.loglikelihood))

    # sum the latitude log likelihood and the longitude log likelihood
    likelihood_for_type = np.asarray(likelihood_lat_for_type) + np.asarray(likelihood_lon_for_type)
    # Calculate the probability
    probs_for_type = Utility.normalise_logprob(likelihood_for_type)
    print('=======================================================')
    this_prediction = {}
    for type_i, this_prob in enumerate(probs_for_type):
        print(ShipTypes[type_i] + ' probability: ' + '{:.2f}'.format(this_prob*100) + '% \t  LL: ' + str(likelihood_for_type[type_i]))
        this_prediction[ShipTypes[type_i]] = likelihood_for_type[type_i]
    print('-------------------------------------------------------')
    # The predictions are here: the log-likelihood of each type (larger log-likelihood means larger probability)
    predictions.append(this_prediction)
