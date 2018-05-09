import React from 'react'
import Select from 'react-select'
import 'react-select/dist/react-select.css'

export default class RuleLine extends React.Component {
    state = {
        selectedSport: '',
        selectedGear: [],
    }
    
    handleSportChange = (selectedOption) => {
        this.setState({ selectedSport: selectedOption });
        console.log(`Selected: ${selectedOption.label}`);
    }

    handleGearChange = (selectedOption) => {
        this.setState({ selectedGear: selectedOption });
        console.log(`Selected: ${selectedOption.label}`);
    }

    handleDelete = (event) => {
        event.preventDefault();
        this.props.handleDelete();
    }

    render() {
        const { selectedSport, selectedGear } = this.state;
        const { sportTypes, gears } = this.props
        const sports = sportTypes.map(function (e) {
            var obj = {};
            obj['value'] = e;
            obj['label'] = e;
            return obj;
        });
        const gearData = gears.map(function (e) {
            var obj = {};
            obj['value'] = e.id;
            obj['label'] = e.name;
            return obj;
        });
        return (
            <div className="ruleRow">
                <span className="ruleSelector">
                    <Select
                        name="sport"
                        placeholder="Select sport"
                        value={selectedSport}
                        onChange={this.handleSportChange}
                        options={sports}
                    />
                </span>
                <span className="ruleSelector">
                    <Select
                        name="inventory"
                        placeholder="Select gear(s)"
                        multi
                        value={selectedGear}
                        onChange={this.handleGearChange}
                        options={gearData}
                    />
                </span>
                <button className="deleteRule" onClick={this.handleDelete} />
            </div>
        );
    }
}