import pytest
import unittest.mock as mock
from datetime import datetime, date, timedelta
import json
from decimal import Decimal

from plugins.emfit import EmfitPlugin, EmfitData, EmfitAPIError, EmfitAuthenticationError


class TestEmfitPlugin:
    """Test suite for EmfitPlugin class"""

    @pytest.fixture
    def emfit_plugin(self):
        """Create an EmfitPlugin instance for testing"""
        return EmfitPlugin(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token"
        )

    @pytest.fixture
    def sample_sleep_data(self):
        """Sample sleep data for testing"""
        return {
            "sleep_start": "2024-01-15T22:30:00Z",
            "sleep_end": "2024-01-16T06:45:00Z",
            "duration": 480,
            "efficiency": 85.5,
            "deep_sleep": 120,
            "light_sleep": 300,
            "rem_sleep": 60,
            "awake_time": 30,
            "hr_avg": 62,
            "hrv": 45.2,
            "respiratory_rate": 14.5,
            "temperature": 36.8,
            "movement": 15,
            "snoring": 5
        }

    @pytest.fixture
    def sample_activity_data(self):
        """Sample activity data for testing"""
        return {
            "date": "2024-01-16",
            "steps": 8540,
            "distance": 6.2,
            "calories": 2250,
            "active_minutes": 85,
            "sedentary_minutes": 480,
            "heart_rate_zones": {
                "fat_burn": 25,
                "cardio": 15,
                "peak": 5
            }
        }

    def test_init_with_valid_credentials(self):
        """Test plugin initialization with valid credentials"""
        plugin = EmfitPlugin(
            client_id="test_client",
            client_secret="test_secret",
            access_token="test_token"
        )
        assert plugin.client_id == "test_client"
        assert plugin.client_secret == "test_secret"
        assert plugin.access_token == "test_token"
        assert plugin.base_url == "https://api.emfit.com/v1"

    def test_init_with_missing_credentials(self):
        """Test plugin initialization with missing credentials"""
        with pytest.raises(ValueError, match="client_id is required"):
            EmfitPlugin(client_id="", client_secret="secret", access_token="token")
        
        with pytest.raises(ValueError, match="client_secret is required"):
            EmfitPlugin(client_id="client", client_secret="", access_token="token")
        
        with pytest.raises(ValueError, match="access_token is required"):
            EmfitPlugin(client_id="client", client_secret="secret", access_token="")

    def test_init_with_none_credentials(self):
        """Test plugin initialization with None credentials"""
        with pytest.raises(ValueError, match="client_id is required"):
            EmfitPlugin(client_id=None, client_secret="secret", access_token="token")

    def test_init_with_custom_base_url(self):
        """Test plugin initialization with custom base URL"""
        plugin = EmfitPlugin(
            client_id="test_client",
            client_secret="test_secret",
            access_token="test_token",
            base_url="https://custom.emfit.com/api"
        )
        assert plugin.base_url == "https://custom.emfit.com/api"

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_success(self, mock_get, emfit_plugin, sample_sleep_data):
        """Test successful sleep data retrieval"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [sample_sleep_data]}
        mock_get.return_value = mock_response

        result = emfit_plugin.get_sleep_data(date(2024, 1, 16))
        
        assert len(result) == 1
        assert result[0]["duration"] == 480
        assert result[0]["efficiency"] == 85.5
        mock_get.assert_called_once()

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_with_date_range(self, mock_get, emfit_plugin, sample_sleep_data):
        """Test sleep data retrieval with date range"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [sample_sleep_data, sample_sleep_data]}
        mock_get.return_value = mock_response

        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 16)
        result = emfit_plugin.get_sleep_data(start_date, end_date)
        
        assert len(result) == 2
        mock_get.assert_called_once()

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_empty_response(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with empty response"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = emfit_plugin.get_sleep_data(date(2024, 1, 16))
        
        assert result == []
        mock_get.assert_called_once()

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_authentication_error(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with authentication error"""
        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid token"}
        mock_get.return_value = mock_response

        with pytest.raises(EmfitAuthenticationError, match="Authentication failed"):
            emfit_plugin.get_sleep_data(date(2024, 1, 16))

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_api_error(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with API error"""
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_get.return_value = mock_response

        with pytest.raises(EmfitAPIError, match="API request failed"):
            emfit_plugin.get_sleep_data(date(2024, 1, 16))

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_network_error(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with network error"""
        mock_get.side_effect = ConnectionError("Network error")

        with pytest.raises(EmfitAPIError, match="Network error"):
            emfit_plugin.get_sleep_data(date(2024, 1, 16))

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_invalid_json(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with invalid JSON response"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        with pytest.raises(EmfitAPIError, match="Invalid JSON response"):
            emfit_plugin.get_sleep_data(date(2024, 1, 16))

    @mock.patch('plugins.emfit.requests.get')
    def test_get_activity_data_success(self, mock_get, emfit_plugin, sample_activity_data):
        """Test successful activity data retrieval"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [sample_activity_data]}
        mock_get.return_value = mock_response

        result = emfit_plugin.get_activity_data(date(2024, 1, 16))
        
        assert len(result) == 1
        assert result[0]["steps"] == 8540
        assert result[0]["distance"] == 6.2
        mock_get.assert_called_once()

    def test_get_sleep_data_invalid_date_type(self, emfit_plugin):
        """Test sleep data retrieval with invalid date type"""
        with pytest.raises(TypeError, match="Date must be a date object"):
            emfit_plugin.get_sleep_data("2024-01-16")

    def test_get_sleep_data_end_date_before_start_date(self, emfit_plugin):
        """Test sleep data retrieval with end date before start date"""
        start_date = date(2024, 1, 16)
        end_date = date(2024, 1, 15)
        
        with pytest.raises(ValueError, match="End date must be after start date"):
            emfit_plugin.get_sleep_data(start_date, end_date)

    def test_get_sleep_data_future_date(self, emfit_plugin):
        """Test sleep data retrieval with future date"""
        future_date = date.today() + timedelta(days=1)
        
        with pytest.raises(ValueError, match="Date cannot be in the future"):
            emfit_plugin.get_sleep_data(future_date)

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_rate_limit_error(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with rate limit error"""
        mock_response = mock.Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_get.return_value = mock_response

        with pytest.raises(EmfitAPIError, match="Rate limit exceeded"):
            emfit_plugin.get_sleep_data(date(2024, 1, 16))

    @mock.patch('plugins.emfit.requests.get')
    def test_get_sleep_data_with_retry_logic(self, mock_get, emfit_plugin):
        """Test sleep data retrieval with retry logic on temporary failure"""
        # First call fails with 503, second call succeeds
        mock_response_fail = mock.Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.json.return_value = {"error": "Service unavailable"}
        
        mock_response_success = mock.Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": []}
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]

        result = emfit_plugin.get_sleep_data(date(2024, 1, 16), retry=True)
        
        assert result == []
        assert mock_get.call_count == 2

    def test_format_sleep_data_complete(self, emfit_plugin, sample_sleep_data):
        """Test formatting complete sleep data"""
        formatted = emfit_plugin.format_sleep_data(sample_sleep_data)
        
        assert formatted["sleep_start"] == datetime.fromisoformat("2024-01-15T22:30:00Z")
        assert formatted["sleep_end"] == datetime.fromisoformat("2024-01-16T06:45:00Z")
        assert formatted["duration_minutes"] == 480
        assert formatted["efficiency_percent"] == 85.5
        assert formatted["deep_sleep_minutes"] == 120
        assert formatted["light_sleep_minutes"] == 300
        assert formatted["rem_sleep_minutes"] == 60
        assert formatted["awake_time_minutes"] == 30

    def test_format_sleep_data_missing_fields(self, emfit_plugin):
        """Test formatting sleep data with missing fields"""
        incomplete_data = {
            "sleep_start": "2024-01-15T22:30:00Z",
            "sleep_end": "2024-01-16T06:45:00Z",
            "duration": 480
        }
        
        formatted = emfit_plugin.format_sleep_data(incomplete_data)
        
        assert formatted["sleep_start"] == datetime.fromisoformat("2024-01-15T22:30:00Z")
        assert formatted["sleep_end"] == datetime.fromisoformat("2024-01-16T06:45:00Z")
        assert formatted["duration_minutes"] == 480
        assert formatted.get("efficiency_percent") is None
        assert formatted.get("deep_sleep_minutes") is None

    def test_format_sleep_data_invalid_datetime(self, emfit_plugin):
        """Test formatting sleep data with invalid datetime format"""
        invalid_data = {
            "sleep_start": "invalid-datetime",
            "sleep_end": "2024-01-16T06:45:00Z",
            "duration": 480
        }
        
        with pytest.raises(ValueError, match="Invalid datetime format"):
            emfit_plugin.format_sleep_data(invalid_data)

    def test_calculate_sleep_metrics(self, emfit_plugin, sample_sleep_data):
        """Test sleep metrics calculation"""
        metrics = emfit_plugin.calculate_sleep_metrics(sample_sleep_data)
        
        assert metrics["total_sleep_time"] == 480
        assert metrics["sleep_efficiency"] == 85.5
        assert metrics["deep_sleep_ratio"] == 0.25  # 120/480
        assert metrics["rem_sleep_ratio"] == 0.125  # 60/480
        assert metrics["wake_after_sleep_onset"] == 30

    def test_calculate_sleep_metrics_zero_duration(self, emfit_plugin):
        """Test sleep metrics calculation with zero duration"""
        zero_duration_data = {
            "duration": 0,
            "deep_sleep": 0,
            "rem_sleep": 0,
            "awake_time": 0
        }
        
        metrics = emfit_plugin.calculate_sleep_metrics(zero_duration_data)
        
        assert metrics["total_sleep_time"] == 0
        assert metrics["deep_sleep_ratio"] == 0
        assert metrics["rem_sleep_ratio"] == 0

    def test_validate_sleep_data_valid(self, emfit_plugin, sample_sleep_data):
        """Test validation of valid sleep data"""
        assert emfit_plugin.validate_sleep_data(sample_sleep_data) is True

    def test_validate_sleep_data_missing_required_fields(self, emfit_plugin):
        """Test validation of sleep data with missing required fields"""
        invalid_data = {
            "sleep_start": "2024-01-15T22:30:00Z",
            # Missing sleep_end and duration
        }
        
        assert emfit_plugin.validate_sleep_data(invalid_data) is False

    def test_validate_sleep_data_negative_values(self, emfit_plugin):
        """Test validation of sleep data with negative values"""
        invalid_data = {
            "sleep_start": "2024-01-15T22:30:00Z",
            "sleep_end": "2024-01-16T06:45:00Z",
            "duration": -480,  # Negative duration
            "efficiency": 85.5
        }
        
        assert emfit_plugin.validate_sleep_data(invalid_data) is False

    def test_validate_sleep_data_invalid_efficiency(self, emfit_plugin):
        """Test validation of sleep data with invalid efficiency values"""
        invalid_data = {
            "sleep_start": "2024-01-15T22:30:00Z",
            "sleep_end": "2024-01-16T06:45:00Z",
            "duration": 480,
            "efficiency": 150  # Efficiency over 100%
        }
        
        assert emfit_plugin.validate_sleep_data(invalid_data) is False

    @mock.patch('plugins.emfit.requests.post')
    def test_refresh_token_success(self, mock_post, emfit_plugin):
        """Test successful token refresh"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        result = emfit_plugin.refresh_token("old_refresh_token")
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert result["expires_in"] == 3600

    @mock.patch('plugins.emfit.requests.post')
    def test_refresh_token_invalid_refresh_token(self, mock_post, emfit_plugin):
        """Test token refresh with invalid refresh token"""
        mock_response = mock.Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_post.return_value = mock_response

        with pytest.raises(EmfitAuthenticationError, match="Invalid refresh token"):
            emfit_plugin.refresh_token("invalid_refresh_token")

    def test_get_date_range_single_date(self, emfit_plugin):
        """Test getting date range for single date"""
        single_date = date(2024, 1, 16)
        start, end = emfit_plugin.get_date_range(single_date)
        
        assert start == single_date
        assert end == single_date

    def test_get_date_range_multiple_dates(self, emfit_plugin):
        """Test getting date range for multiple dates"""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 17)
        start, end = emfit_plugin.get_date_range(start_date, end_date)
        
        assert start == start_date
        assert end == end_date

    def test_build_api_url_sleep_data(self, emfit_plugin):
        """Test building API URL for sleep data"""
        test_date = date(2024, 1, 16)
        url = emfit_plugin.build_api_url("sleep", test_date)
        
        expected = f"{emfit_plugin.base_url}/sleep?date=2024-01-16"
        assert url == expected

    def test_build_api_url_activity_data_with_range(self, emfit_plugin):
        """Test building API URL for activity data with date range"""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 17)
        url = emfit_plugin.build_api_url("activity", start_date, end_date)
        
        expected = f"{emfit_plugin.base_url}/activity?start_date=2024-01-15&end_date=2024-01-17"
        assert url == expected

    def test_build_api_url_invalid_endpoint(self, emfit_plugin):
        """Test building API URL with invalid endpoint"""
        with pytest.raises(ValueError, match="Invalid endpoint"):
            emfit_plugin.build_api_url("invalid_endpoint", date(2024, 1, 16))

    @mock.patch('plugins.emfit.time.sleep')
    def test_rate_limit_handling(self, mock_sleep, emfit_plugin):
        """Test rate limit handling with exponential backoff"""
        with mock.patch.object(emfit_plugin, '_make_request') as mock_request:
            mock_request.side_effect = [
                EmfitAPIError("Rate limit exceeded"),
                EmfitAPIError("Rate limit exceeded"),
                {"data": []}
            ]
            
            result = emfit_plugin.get_sleep_data(date(2024, 1, 16), retry=True)
            
            assert result == []
            assert mock_request.call_count == 3
            assert mock_sleep.call_count == 2

    def test_data_aggregation_weekly(self, emfit_plugin, sample_sleep_data):
        """Test weekly sleep data aggregation"""
        week_data = [sample_sleep_data] * 7
        
        aggregated = emfit_plugin.aggregate_sleep_data(week_data, period="weekly")
        
        assert aggregated["avg_duration"] == 480
        assert aggregated["avg_efficiency"] == 85.5
        assert aggregated["total_nights"] == 7

    def test_data_aggregation_monthly(self, emfit_plugin, sample_sleep_data):
        """Test monthly sleep data aggregation"""
        month_data = [sample_sleep_data] * 30
        
        aggregated = emfit_plugin.aggregate_sleep_data(month_data, period="monthly")
        
        assert aggregated["avg_duration"] == 480
        assert aggregated["avg_efficiency"] == 85.5
        assert aggregated["total_nights"] == 30

    def test_data_aggregation_empty_data(self, emfit_plugin):
        """Test data aggregation with empty data"""
        aggregated = emfit_plugin.aggregate_sleep_data([], period="weekly")
        
        assert aggregated["avg_duration"] == 0
        assert aggregated["avg_efficiency"] == 0
        assert aggregated["total_nights"] == 0

    def test_data_aggregation_invalid_period(self, emfit_plugin, sample_sleep_data):
        """Test data aggregation with invalid period"""
        with pytest.raises(ValueError, match="Invalid aggregation period"):
            emfit_plugin.aggregate_sleep_data([sample_sleep_data], period="invalid")


class TestEmfitData:
    """Test suite for EmfitData class"""

    def test_emfit_data_initialization(self):
        """Test EmfitData initialization"""
        data = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        assert data.sleep_start == datetime(2024, 1, 15, 22, 30)
        assert data.sleep_end == datetime(2024, 1, 16, 6, 45)
        assert data.duration == 480
        assert data.efficiency == 85.5

    def test_emfit_data_to_dict(self):
        """Test EmfitData to_dict method"""
        data = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        result = data.to_dict()
        
        assert result["sleep_start"] == datetime(2024, 1, 15, 22, 30)
        assert result["sleep_end"] == datetime(2024, 1, 16, 6, 45)
        assert result["duration"] == 480
        assert result["efficiency"] == 85.5

    def test_emfit_data_from_dict(self):
        """Test EmfitData from_dict class method"""
        data_dict = {
            "sleep_start": datetime(2024, 1, 15, 22, 30),
            "sleep_end": datetime(2024, 1, 16, 6, 45),
            "duration": 480,
            "efficiency": 85.5
        }
        
        data = EmfitData.from_dict(data_dict)
        
        assert data.sleep_start == datetime(2024, 1, 15, 22, 30)
        assert data.sleep_end == datetime(2024, 1, 16, 6, 45)
        assert data.duration == 480
        assert data.efficiency == 85.5

    def test_emfit_data_str_representation(self):
        """Test EmfitData string representation"""
        data = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        str_repr = str(data)
        assert "EmfitData" in str_repr
        assert "480" in str_repr
        assert "85.5" in str_repr

    def test_emfit_data_equality(self):
        """Test EmfitData equality comparison"""
        data1 = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        data2 = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        assert data1 == data2

    def test_emfit_data_inequality(self):
        """Test EmfitData inequality comparison"""
        data1 = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=480,
            efficiency=85.5
        )
        
        data2 = EmfitData(
            sleep_start=datetime(2024, 1, 15, 22, 30),
            sleep_end=datetime(2024, 1, 16, 6, 45),
            duration=490,  # Different duration
            efficiency=85.5
        )
        
        assert data1 != data2


class TestEmfitExceptions:
    """Test suite for Emfit custom exceptions"""

    def test_emfit_api_error_initialization(self):
        """Test EmfitAPIError initialization"""
        error = EmfitAPIError("Test error message", status_code=500)
        
        assert str(error) == "Test error message"
        assert error.status_code == 500

    def test_emfit_api_error_without_status_code(self):
        """Test EmfitAPIError initialization without status code"""
        error = EmfitAPIError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.status_code is None

    def test_emfit_authentication_error_initialization(self):
        """Test EmfitAuthenticationError initialization"""
        error = EmfitAuthenticationError("Authentication failed")
        
        assert str(error) == "Authentication failed"
        assert isinstance(error, EmfitAPIError)

    def test_emfit_authentication_error_with_status_code(self):
        """Test EmfitAuthenticationError initialization with status code"""
        error = EmfitAuthenticationError("Authentication failed", status_code=401)
        
        assert str(error) == "Authentication failed"
        assert error.status_code == 401


class TestEmfitIntegration:
    """Integration tests for Emfit plugin"""

    @pytest.fixture
    def emfit_plugin_with_mock_responses(self):
        """Create plugin with mocked HTTP responses"""
        plugin = EmfitPlugin(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access_token"
        )
        return plugin

    @mock.patch('plugins.emfit.requests.get')
    def test_end_to_end_sleep_data_retrieval(self, mock_get, emfit_plugin_with_mock_responses):
        """Test end-to-end sleep data retrieval and processing"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "sleep_start": "2024-01-15T22:30:00Z",
                    "sleep_end": "2024-01-16T06:45:00Z",
                    "duration": 480,
                    "efficiency": 85.5,
                    "deep_sleep": 120,
                    "light_sleep": 300,
                    "rem_sleep": 60,
                    "awake_time": 30
                }
            ]
        }
        mock_get.return_value = mock_response

        # Get raw data
        raw_data = emfit_plugin_with_mock_responses.get_sleep_data(date(2024, 1, 16))
        
        # Format data
        formatted_data = emfit_plugin_with_mock_responses.format_sleep_data(raw_data[0])
        
        # Validate data
        is_valid = emfit_plugin_with_mock_responses.validate_sleep_data(raw_data[0])
        
        # Calculate metrics
        metrics = emfit_plugin_with_mock_responses.calculate_sleep_metrics(raw_data[0])
        
        assert len(raw_data) == 1
        assert formatted_data["duration_minutes"] == 480
        assert is_valid is True
        assert metrics["sleep_efficiency"] == 85.5

    @mock.patch('plugins.emfit.requests.get')
    def test_data_consistency_across_date_ranges(self, mock_get, emfit_plugin_with_mock_responses):
        """Test data consistency when retrieving across different date ranges"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "sleep_start": "2024-01-15T22:30:00Z",
                    "sleep_end": "2024-01-16T06:45:00Z",
                    "duration": 480,
                    "efficiency": 85.5
                },
                {
                    "sleep_start": "2024-01-16T23:00:00Z",
                    "sleep_end": "2024-01-17T07:00:00Z",
                    "duration": 480,
                    "efficiency": 87.0
                }
            ]
        }
        mock_get.return_value = mock_response

        # Get data for date range
        range_data = emfit_plugin_with_mock_responses.get_sleep_data(
            date(2024, 1, 15), 
            date(2024, 1, 16)
        )
        
        # Aggregate data
        aggregated = emfit_plugin_with_mock_responses.aggregate_sleep_data(
            range_data, 
            period="weekly"
        )
        
        assert len(range_data) == 2
        assert aggregated["avg_efficiency"] == 86.25  # (85.5 + 87.0) / 2
        assert aggregated["total_nights"] == 2

    def test_plugin_configuration_validation(self):
        """Test plugin configuration validation edge cases"""
        # Test with whitespace-only credentials
        with pytest.raises(ValueError):
            EmfitPlugin(client_id="   ", client_secret="secret", access_token="token")
        
        # Test with very long credentials
        long_string = "a" * 1000
        plugin = EmfitPlugin(
            client_id=long_string,
            client_secret=long_string,
            access_token=long_string
        )
        assert len(plugin.client_id) == 1000

    def test_concurrent_request_handling(self, emfit_plugin_with_mock_responses):
        """Test handling of concurrent requests (thread safety)"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                with mock.patch('plugins.emfit.requests.get') as mock_get:
                    mock_response = mock.Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"data": []}
                    mock_get.return_value = mock_response
                    
                    time.sleep(0.01)  # Simulate API delay
                    result = emfit_plugin_with_mock_responses.get_sleep_data(date(2024, 1, 16))
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create and start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests completed successfully
        assert len(results) == 10
        assert len(errors) == 0
        assert all(result == [] for result in results)


if __name__ == "__main__":
    pytest.main([__file__])