from typing import Dict

# Define a type alias
ClusterPreferenceDataType = Dict[int, Dict[str, float]]


# TODO: - write test cases for this
class ClusterPreferenceData:
    def __init__(self, data: ClusterPreferenceDataType):
        self.data = data
        self._validate()

    def _validate(self) -> None:
        assert isinstance(self.data, dict), "data must be a dictionary."

        for key, value in self.data.items():
            assert isinstance(key, int), f"Key {key} is not an int."
            assert isinstance(value, dict), f"Value {value} for key {key} is not a dictionary."
            assert 'a' in value and 'b' in value, "Both 'a' and 'b' must be present in the sub-dictionary."
            assert isinstance(value.get('a'), float) and isinstance(value.get('b'), float), f"Values in sub-dictionary is not a float."

    def get_data(self) -> ClusterPreferenceDataType:
        return self.data

    def update_data(self, new_cluster_preferences: ClusterPreferenceDataType) -> None:
        self.data = new_cluster_preferences
        self._validate()

    def get_cluster_data(self, cluster_id: int) -> Dict[str, float]:
        return self.data.get(cluster_id, {})

    def get_cluster_a_data(self, cluster_id: int) -> float:
        return self.get_cluster_data(cluster_id=cluster_id).get('a', 1.0)

    def update_cluster_data(self, cluster_id: int, new_preference: Dict[str, float]) -> None:
        self.data[cluster_id] = new_preference
        self._validate()

    def update_cluster_a_data(self, cluster_id: int, new_a: float) -> None:
        self.data[cluster_id]['a'] = new_a
        self._validate()
#
# # Example usage
# try:
#     valid_data = {1: {'ts_clicked': 1.0, 'ts_not_clicked': 2.0}}
#     cluster_pref = ClusterPreferenceData(valid_data)
#     print("Data is valid.")
#
#     # Retrieve all data
#     all_data = cluster_pref.get_data()
#     print("All data:", all_data)
#
#     # Retrieve specific cluster data
#     cluster_data = cluster_pref.get_cluster_data(1)
#     print("Cluster data:", cluster_data)
#
#     # Update specific cluster data
#     new_data = {'ts_clicked': 5.0, 'ts_not_clicked': 6.0}
#     cluster_pref.update_cluster_data(1, new_data)
#     updated_cluster_data = cluster_pref.get_cluster_data(1)
#     print("Updated cluster data:", updated_cluster_data)
#
# except AssertionError as e:
#     print(f"AssertionError: {e}")
