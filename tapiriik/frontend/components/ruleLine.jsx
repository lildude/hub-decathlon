import React from 'react'
import Select from 'react-select'
import 'react-select/dist/react-select.css'

export default class RuleLine extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            id: props.data.id,
            selectedSport: props.data.selectedSport,
            selectedGear: props.data.selectedGear,
        }
    }
    
    handleSportChange = (selectedOption) => {
        var sport = '';
        if (selectedOption) {
            sport = selectedOption.value;
        }
        this.setState({ selectedSport: sport }, () => {
            this.props.handleChange(this.state);
        });
        console.log(`Selected: ${sport}`);
    }

    handleGearChange = (selectedOption) => {
        var gear = [];
        if (selectedOption) {
            gear = selectedOption.map((o) => o.value);
        }
        this.setState({ selectedGear: gear }, () => {
            this.props.handleChange(this.state);
        });
        console.log(`Selected: ${gear}`);
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
                        onChange={(obj) => this.handleSportChange(obj)}
                        options={sports}
                    />
                </span>
                <span className="ruleSelector">
                    <Select
                        name="inventory"
                        placeholder="Select gear(s)"
                        multi
                        value={selectedGear}
                        onChange={(obj) => this.handleGearChange(obj)}
                        options={gearData}
                    />
                </span>
                <button className="deleteRule" onClick={this.handleDelete} />
            </div>
        );
    }
}